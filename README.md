# TG Exporter

**TG 导出器**：Windows Telegram GUI 导出器 + 本地 `tgctl` 机器接口。

> 正式 Release 当前仍为 v0.1.10。`codex/personal-account-reader-v0.3.0` 是第三代 **v0.3.0 candidate** 开发线，完成验收前不发布 Release。

历史本地目录继续固定为：

```text
%APPDATA%\TelegramMultiChatExporter\
```

## 三代关系

```text
v0.1.x  GUI exporter + direct-session tgctl
   ↓
v0.2.0  single daemon + Windows Named Pipe IPC
   ↓
v0.3.0  v0.2 daemon + Personal Account Reader
```

v0.3.0 不重新制造 GUI/tgctl Session 竞争：GUI、tgctl、Codex 都通过同一个后台 daemon 使用唯一 Telegram Session。

## GUI 体验

GUI 继续保持已验证的多群独立导出体验：

- 工作群选择、Telegram Chat Folder、群头像；
- 本地 Export Category；
- 指定时间范围 / 当前未读 / 上次成功导出以后；
- `总输出目录 / 分类 / 群组 / YYYY-MM-DD_HH-mm-ss.json`；
- 每次 JSON 独立，不合并、不覆盖历史；
- Basic Group → Supergroup migration collapse；
- current unread 默认只读；可选“导出后标已读”严格遵守 `JSON success → checkpoint → optional read ack`。

第二代 daemon 体验继续保留：关闭 GUI 后正在运行的导出可以继续；Codex/tgctl 可按需唤醒 daemon；后台有 Windows 托盘；空闲约 10 分钟自动退出。导出期间 Telegram reader 等待，真实 send/forward 直接拒绝而不是悄悄排队发送。

## v0.3.0 Personal Account Reader

第三代目标是让本地 Codex 不依赖 GUI 导出文件，也能通过 `tgctl` 安全、分页地读取当前个人 Telegram 账号有权访问的信息。

### 账号与完整会话目录

```powershell
tgctl account get --json
tgctl dialogs list --limit 100 --json
tgctl dialogs list --type private --unread yes --jsonl
tgctl dialogs list --folder "保研" --cursor <token> --json
```

`dialogs list` 覆盖群、超级群、频道、私聊、Bot、Saved Messages、归档、Telegram Chat Folder、forum/unread/pinned/muted 等安全字段；不输出 `access_hash`。

### 会话详情、群主与管理员

```powershell
tgctl chats get --chat <ref> --json
tgctl chats members --chat <ref> --role owner --json
tgctl chats members --chat <ref> --role admin --limit 100 --jsonl
```

成员身份来自 Telegram participant/admin 数据，不通过显示名猜测。`owner/admin/member` 表示查询时当前角色；匿名管理员和 send-as 消息不会被伪造归属到某个具体用户。

### 完整历史分页

```powershell
tgctl messages history --chat <ref> --limit 100 --json
tgctl messages history --chat <ref> --cursor <token> --limit 100 --json
tgctl messages history --chat me --since 2026-08-01 --until 2026-09-01 --jsonl
```

默认 100 条/页，最大 500。不会静默无限读取整个历史。`since` inclusive、`until` exclusive。读取本身不推进 Telegram read marker，也不下载媒体。

Rich message schema 包含安全可得的：结构化 sender、reply、forum topic、forward origin、entities、views、forwards、reactions、poll、service action、media metadata 等。缺失消息仍返回 `MESSAGE_NOT_FOUND`，不会把“查不到”武断解释为“已删除”。

### 高级搜索

```powershell
tgctl messages search --chat <ref> --contains "pikpak" --limit 500 --json
tgctl messages search --chat <ref> --sender-role admin --contains "pikpak" --json
tgctl messages search --chat <ref> --url-domain mypikpak.com --json
tgctl messages search --contains "预推免" --limit 100 --jsonl
```

支持单会话与全局、sender-id、当前 sender-role、时间范围、message type、forum topic、是否含链接、真实 URL hostname、cursor/limit。`--url-domain mypikpak.com` 会解析 hostname，`mypikpak.com.evil.com` 不会被误判为目标域名。

### Forum Topic

```powershell
tgctl topics list --chat <forum> --json
tgctl topics history --chat <forum> --topic <id> --limit 100 --jsonl
```

非 forum 会话返回 `NOT_A_FORUM`。

### 媒体

历史/search/get 默认只返回 metadata，不自动下载。

显式下载采用两阶段确认：

```powershell
tgctl media download --chat <ref> --ids 123 456 --output D:\TGMedia --json
```

第一次只返回文件数量、已知预计大小、未知大小数量和 `confirmation_token`，不会创建目标目录或下载文件。确认后：

```powershell
tgctl media download --chat <ref> --ids 123 456 --output D:\TGMedia --confirm <token> --json
```

普通上限为 20 files / 500 MiB；显式 `--allow-large-download` 后硬上限为 200 files / 5 GiB。文件使用 `.part` 临时文件，成功后原子 rename；token 绑定 chat/ids/output/大小计划并有短时有效期。

## JSON / JSONL

普通 JSON envelope：

```json
{"ok":true,"data":{}}
```

错误：

```json
{"ok":false,"error":{"code":"...","message":"...","details":{}}}
```

大量 reader 页支持 `--jsonl`：

```json
{"type":"meta","ok":true,"data":{"schema":"tgctl.reader.v1"}}
{"type":"item","data":{}}
{"type":"end","data":{"count":1,"next_cursor":"...","has_more":true}}
```

stdout 的消息正文只在用户明确执行 reader 命令时返回；普通 `app.log` 不记录消息正文。

## 写操作边界

现有 `send` / `forward` 保留兼容，但第三代 reader 不扩大授权：

```powershell
tgctl forward --from <chat> --to me --ids 123 --dry-run --json
tgctl send --to me --text "test" --dry-run --json
```

- forward 必须是真正 Telegram forward；
- send 第一代能力仍限纯文本；
- forward 默认最多 20 条，显式大批量最多 200；
- FloodWait 结构化返回，不自动重试风暴；
- 写请求返回前连接中断时不得自动重发；
- 登录 phone/OTP/2FA 仍只在 GUI。

## Session / daemon

v0.3 正常情况：

```text
GUI ─┐
     ├→ TG daemon → TelegramService → telegram.session
tgctl┘
```

所以 v0.3 GUI 与 v0.3 tgctl 可以同时存在，不应出现旧版 GUI↔tgctl `SESSION_BUSY`。

`SESSION_BUSY` 只作为兼容边界：如果旧 v0.1.x/direct process 已经 OS-lock 同一 Session，daemon 安全失败，打包版 `tgctl` 必须返回结构化 `SESSION_BUSY` 且 native exit code = 8。

## 安全

严禁 stdout/log/cursor 暴露：`api_id/api_hash`、手机号、OTP、2FA、Session 内容、credentials 原文、Telegram `access_hash`、`file_reference`、IPC auth secret。

Secret Chat、已删除内容恢复、无权访问内容、自动转发规则、24/7 listener、群管理/删消息/退群等不属于 v0.3 reader 范围。

完整边界见 [`SECURITY.md`](SECURITY.md)。

## 开发与交接

Agent/Codex 修改前依次阅读：

1. [`AGENTS.md`](AGENTS.md)
2. [`HANDOFF.md`](HANDOFF.md)
3. [`docs/PERSONAL_ACCOUNT_READER_V3_DESIGN.md`](docs/PERSONAL_ACCOUNT_READER_V3_DESIGN.md)
4. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
5. [`docs/DECISIONS.md`](docs/DECISIONS.md)
6. [`docs/TESTING.md`](docs/TESTING.md)
7. [`SECURITY.md`](SECURITY.md)
8. [`docs/CODEX_TGCTL.md`](docs/CODEX_TGCTL.md)

开发运行：

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
python -m telegram_exporter
python -m telegram_exporter.tgctl dialogs list --limit 20 --json
```

## Release

正式 Release 仍从 GitHub Releases 分发。**当前 v0.3.0 分支只产出 candidate，未经用户真实账号验收与明确发布授权，不创建或覆盖 v0.3.0 Release。**

## License

MIT License，见 [`LICENSE`](LICENSE)。
