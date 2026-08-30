# TG Exporter

**TG 导出器**：面向 Windows 的 Telegram 多群文本导出工具，并提供可被 Codex 调用的本地 `tgctl` 机器接口。

历史本地数据目录固定为：

```text
%APPDATA%\TelegramMultiChatExporter\
```

该路径包含登录 Session/配置兼容性，品牌改名后也继续沿用。

## 当前版本状态

- 正式 Production Release：**v0.1.10**；
- Latest Release：<https://github.com/3ll3-3ll3/tg-exporter/releases/latest>；
- 当前第三代开发：**v0.3.0 Personal Account Reader Candidate**，Draft PR #20；
- v0.3 在真实 Telegram 账号 E2E 与用户明确发布授权前不合并、不发布。

普通用户应使用 GitHub Release；Actions Candidate Artifact 只用于开发验收。

## GUI 核心能力

- 可选择多个 Telegram 群/频道作为 focused workspace；
- 可读取 Telegram Chat Folders / Dialog Filters 辅助筛选；
- 选择器显示群头像并按需缓存；
- 软件内创建 Export Category；
- 每群独立选择指定时间范围、当前未读、上次成功导出以后；
- 输出长期保持：

```text
总输出目录/
└─ 分类/
   └─ 群组/
      ├─ 2026-08-29_18-55-01.json
      └─ 2026-08-31_20-10-22.json
```

每次 JSON 独立，不读取/合并/覆盖历史；同秒冲突自动 `_2/_3/...`。

GUI 消息导出默认只保留文字/caption，不下载照片、视频、文件、语音或贴纸。群头像只是选择器 UI cache，不进入导出 JSON。

Telegram Chat Folder 与 Export Category 不同：前者来自 Telegram 账号、只读、用于找群；后者由 TG Exporter 本地管理，用于决定 JSON 文件夹。

## Basic Group → Supergroup

普通群升级为超级群后：

- catalogue 只显示当前 Supergroup；
- legacy Basic Group 仅用于读取迁移前历史；
- 不按同名猜迁移关系；
- 不删除/退出/修改真实 Supergroup；
- 指定时间范围可以读取 current + legacy；
- current unread / since-last 只针对当前 Supergroup。

## 当前未读与标已读

current unread 使用冻结边界。每群“导出后标已读”默认关闭，且只对 current-unread 模式生效。

严格顺序：

```text
JSON 原子写入成功
→ checkpoint 更新
→ 可选 Telegram read acknowledgement
```

导出失败绝不推进 read marker；read ack 失败也不会删除已经成功的 JSON。

## v0.1.10 tgctl

正式 v0.1.10 附带 `tgctl.exe`，复用 GUI 已登录的 Telegram 用户 Session，不使用 Bot API，也不重新做 CLI phone/OTP/2FA 登录。

```powershell
tgctl status --json
tgctl chats list --folder "保研" --search "统计" --json
tgctl messages search --chat <chat_id> --contains "预推免" --json
tgctl messages get --chat <chat_id> --ids 123 456 --json
tgctl forward --from <chat_id> --to me --ids 123 --dry-run --json
tgctl send --to me --text "test" --dry-run --json
```

写操作安全边界：true forward、纯文本 send、dry-run、forward 默认 20 / explicit large hard cap 200、同名 `AMBIGUOUS_CHAT`、FloodWait structured stop、普通日志不记录正文。

v0.1.x GUI 与 tgctl 通过 OS Session lock 防止同时打开同一 Telethon SQLiteSession；冲突时安全返回 `SESSION_BUSY`。v0.1.10 修复了 packaged Windows 中文 JSON 导致 `SESSION_BUSY` native exit code 从 8 退成 1 的问题。

## v0.3 Candidate 方向

第三代继承 v0.2 single-daemon：

```text
TGExporter GUI ─┐
                ├→ local authenticated Named Pipe → TG daemon → Telegram user Session
 tgctl / Codex ─┘
```

v0.3 Candidate 增加账号/全部 dialogs、chat details、members/owner/admin、分页 history、rich messages、advanced search、Forum、Saved Messages、media metadata 与显式两阶段媒体下载。

它仍不是后台自动监听 Agent：reader 默认 Telegram read-only；MCP、24/7 listener、自动转发规则、AI 自主分类不属于当前版本。

开发状态与真人 E2E 下载信息以 [`HANDOFF.md`](HANDOFF.md) 和 Draft PR #20 为准。

## 本地数据与安全

公开仓库/Issue/PR/CI/普通日志禁止出现：

- Telegram `api_id/api_hash`；
- phone / OTP / 2FA；
- `*.session` / credentials；
- Telegram `access_hash` / `file_reference`；
- IPC auth secret；
- 用户真实聊天正文、导出结果或头像 cache。

完整规则：[`SECURITY.md`](SECURITY.md) 与 [`docs/SECURITY_MODEL.md`](docs/SECURITY_MODEL.md)。

## 开发

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
python -m telegram_exporter
```

正式 Windows Release 通过 GitHub Actions / GitHub Releases 构建和分发；详见 [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) 与 [`docs/RELEASE_PROCESS.md`](docs/RELEASE_PROCESS.md)。

## Agent / 新对话接手

**不要只读 README 就修改。** 固定入口：

1. [`AGENTS.md`](AGENTS.md)
2. [`HANDOFF.md`](HANDOFF.md)
3. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
4. [`docs/SECURITY_MODEL.md`](docs/SECURITY_MODEL.md)
5. [`docs/TESTING.md`](docs/TESTING.md)
6. [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md)
7. 与当前任务相关的 [`docs/decisions/`](docs/decisions/) ADR
8. 当前 PR/Branch/CI/Release

当前工作的准确恢复步骤写在 `HANDOFF.md` 的 **New Chat Resume Instructions**。

## License

MIT License，见 [`LICENSE`](LICENSE)。