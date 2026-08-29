# TG Exporter

**TG 导出器**：一个面向 Windows 的 Telegram 多群文本消息导出工具；v0.1.9 起同时提供可被 Codex 调用的本地 `tgctl` CLI Bridge。

> 为避免升级后丢失登录状态和配置，历史本地数据目录 `%APPDATA%\TelegramMultiChatExporter\` 继续沿用。

## 核心目标

- GUI 继续作为日常导出主入口。
- Telegram 账号里的全部群组只作为**群组目录**加载；主编辑面板只显示主动选择的工作群。
- “选择群组”可读取 Telegram 账号已有的 Chat Folders / Dialog Filters，并显示群头像帮助识别。
- 每个工作群拥有独立导出规则与导出分类：指定时间范围、当前未读、上次成功导出以后。
- 输出结构：`总输出目录 / 分类 / 群组 / 日期时间.json`；每次结果独立，不合并、不覆盖历史。
- 消息导出只保留文字/caption，不下载聊天媒体。
- 普通群升级为超级群后，只显示当前 Supergroup；指定时间范围可补取迁移前历史。
- Telegram 登录凭据和 `.session` 仅存放本机。
- `tgctl` 复用同一个 Telegram 用户 Session，为 Codex 提供列群、搜消息、取消息、真正转发和纯文本发送能力。

## GUI 日常使用

1. 首次打开 EXE，输入 Telegram `api_id` / `api_hash` 并登录。
2. 点击 **选择群组**，可先按 Telegram 分组缩小范围，再用头像/群名/`@username` 选择工作群。
3. 点击 **管理分类**，创建“第一类 / 第二类 / 保研 / AI / 资料”等本地导出分类。
4. 主表格为每个工作群选择分类、导出方式和日期范围。
5. 点击 **开始导出**。

输出示例：

```text
D:\TG导出\
├─ 第一类\
│  ├─ 群组1\
│  │  ├─ 2026-08-29_18-55-01.json
│  │  └─ 2026-08-31_20-10-22.json
│  └─ 群组2\
│     └─ 2026-08-29_18-55-01.json
└─ 第二类\
   ├─ 群组3\
   ├─ 群组4\
   └─ 群组5\
```

同一群同一秒重复导出自动追加 `_2`、`_3`，不会覆盖旧文件。软件内删除分类也不会删除磁盘历史数据。

Telegram Chat Folder 与 Export Category 是两件不同的事：前者来自账号、只读、用于选择群；后者由 TG Exporter 在本机管理，用于决定 JSON 落盘目录。

## 普通群升级为超级群

Telegram 底层在 Basic Group 升级为 Supergroup 后会保留旧 Chat peer。TG Exporter 从 v0.1.8 起：

- catalogue 只显示当前 Supergroup；
- 不删除、不退出、不修改或降级真实超级群；
- 迁移前旧群只作为内部历史来源；
- 旧工作区/分类/标已读偏好尽量迁到当前 Supergroup；
- 当前未读、上次导出以后只操作当前 Supergroup；
- 指定时间范围可读取 legacy + current，再按时间合并。

## 三种导出模式

### 指定时间范围

按该群自己的开始/结束日期导出。若群由 Basic Group 升级而来，会在检测到 migration relation 时读取迁移前历史。

### 当前未读

刷新 catalogue 时冻结 Telegram 已读边界与最新消息位置。默认只读，不改变 Telegram read marker。

每群有独立 **导出后标已读** 开关：默认关闭，只在“当前未读”模式可用。严格顺序为：JSON 成功写入 → checkpoint 更新 → 可选 read acknowledgement。导出失败绝不标已读；read ack 失败也不删除已成功 JSON。

### 上次导出以后

使用本工具本地保存的最后成功导出位置，与 Telegram 官方客户端的“未读”状态无关。

## Codex / tgctl 本地 Telegram Bridge

v0.1.9 起正式 Release 附带 `tgctl.exe`。它不使用 Bot API，不重新登录，而是复用：

```text
%APPDATA%\TelegramMultiChatExporter\api_credentials.json
%APPDATA%\TelegramMultiChatExporter\telegram.session
```

以及现有 Windows system proxy detection。

如果尚未通过 GUI 登录，tgctl 会返回 `NOT_AUTHORIZED` 并提示先打开 TG Exporter，不会在 CLI 重新询问手机号/验证码/2FA。

第一版命令：

```powershell
tgctl status --json
tgctl chats list --folder "保研" --search "统计" --json
tgctl messages search --chat -1001234567890 --contains "预推免" --limit 20 --json
tgctl messages get --chat -1001234567890 --ids 123 456 --json
tgctl forward --from -1001234567890 --to me --ids 123 456 --dry-run --json
tgctl send --to me --text "TG Exporter Codex bridge test" --dry-run --json
```

`--to me` 表示 Saved Messages / 我的收藏。`forward` 使用 Telethon 真正 forward，不会默认复制文本后重新发送。真实 write operation 推荐始终：**先 dry-run → 用户确认 → 再去掉 `--dry-run`**。

forward 默认单次最多 20 条；显式 `--allow-large-batch` 后最多 200 条。FloodWait 不自动疯狂重试，而是返回结构化 `FLOOD_WAIT` 和等待秒数。

JSON 模式 stdout 只输出机器可读 envelope：

```json
{"ok":true,"data":{}}
```

失败：

```json
{"ok":false,"error":{"code":"AMBIGUOUS_CHAT","message":"...","details":[]}}
```

同名群不会被偷偷选择；会返回候选 chat_id 让 Codex 再指定。

### GUI 与 tgctl 不能同时占用 Session

Telethon 默认使用 SQLiteSession。同一 Session 被多个进程同时使用存在 SQLite lock / 更新冲突风险，因此 v0.1.9 给 GUI 与 CLI 加了同一 OS Session lock。

第一版使用 `tgctl` 时请关闭 TG Exporter GUI。如果另一个进程已经占用 Session，后启动者返回 `SESSION_BUSY`，而不是冒险并发打开 `.session`。

完整说明、JSON schema、退出码、Codex Prompt 和真人 E2E checklist：[`docs/CODEX_TGCTL.md`](docs/CODEX_TGCTL.md)。

## Telegram 连接、代理与诊断

- API 设置、重置登录、打开日志目录仍由 GUI 提供。
- 常见 Telegram API / OTP / 2FA / Flood Wait / 网络错误会转换成友好提示。
- Windows system proxy 会显式传给 Telethon；Clash/Mihomo 常见 `127.0.0.1:7890` 场景可直接使用。
- qasync GUI 继续使用单事件循环 + 非阻塞 dialog。
- 群头像采用可见项按需加载，本机缓存约 7 天，不进入导出 JSON。

日志：

```text
%APPDATA%\TelegramMultiChatExporter\logs\app.log
```

头像缓存：

```text
%APPDATA%\TelegramMultiChatExporter\cache\avatars\
```

日志不会主动记录 `api_hash`、手机号、验证码、2FA 密码、Session 内容或聊天正文。tgctl 写操作日志同样只记录动作、chat/message id、数量和结果。

## Release 下载

正式版本只通过 GitHub Releases 分发：

- `TGExporter-vX.Y.Z-windows-x64.exe`；
- `TGExporter-vX.Y.Z-windows-x64-portable.zip`（v0.1.9 起内含 `tgctl.exe`）；
- `tgctl.exe`；
- `SHA256SUMS.txt`。

最新版：

```text
https://github.com/3ll3-3ll3/tg-exporter/releases/latest
```

## 开发者 / Agent 接手

不要只读 README 就修改。固定阅读顺序：

1. [`AGENTS.md`](AGENTS.md)
2. [`HANDOFF.md`](HANDOFF.md)
3. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
4. [`docs/DECISIONS.md`](docs/DECISIONS.md)
5. [`docs/TESTING.md`](docs/TESTING.md)
6. [`docs/RELEASE_PROCESS.md`](docs/RELEASE_PROCESS.md)
7. [`docs/JSON_COMPATIBILITY.md`](docs/JSON_COMPATIBILITY.md)
8. [`SECURITY.md`](SECURITY.md)
9. [`docs/CODEX_TGCTL.md`](docs/CODEX_TGCTL.md)

重大功能、关键 bug、Release 或用户真实 E2E 结果完成后必须同步更新 `HANDOFF.md`。

## 开发运行

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python -m telegram_exporter
python -m telegram_exporter.tgctl status --json
```

安装后：

```powershell
tg-exporter
tgctl status --json
```

旧 GUI 命令 `telegram-multi-chat-exporter` 暂时保留兼容。

## License

MIT License，见 [`LICENSE`](LICENSE)。

## 安全

公开仓库禁止提交 Telegram `api_hash`、手机号、验证码、2FA 密码、`*.session`、本地日志、真实聊天正文、头像缓存和本地导出结果。完整规则见 [`SECURITY.md`](SECURITY.md)。
