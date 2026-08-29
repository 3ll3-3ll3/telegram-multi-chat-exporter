# HANDOFF.md

> 当前开发交接快照。任何 Agent 接手前先读 `AGENTS.md`，再读本文件。

更新时间：2026-08-29

## 1. 当前正式版本

- 当前正式版：**TG Exporter v0.1.9**
- Release：`https://github.com/3ll3-3ll3/tg-exporter/releases/tag/v0.1.9`
- PR：`#16`
- merge commit：`22014f5999867e5d0b0e6c1e46320320fc974cd0`
- Release target：同上
- Release workflow：`33258806323`，结论 success

正式资产 SHA-256：

- `TGExporter-v0.1.9-windows-x64.exe`
  - `b2e349a7165de106f3f338df1fa44061b152ad70b0c1d71370c81758b98529cf`
- `TGExporter-v0.1.9-windows-x64-portable.zip`
  - `42af909157a624d5bc58fddb60b4f4bf6a520d9fe017a7ba115dbd2ea84f3d22`
- `tgctl.exe`
  - `028fee5cec1ec6d28edee5e51a605a1560bca9188636d10dec37abc0eb35de53`

## 2. v0.1.8 真人验证仍视为通过

用户在 2026-08-29 明确反馈此前功能“都验证通过”。包括：

- 软件内 Export Category 创建/保存/目录自动生成；
- `output/category/group/timestamp.json` 长期目录结构；
- 群分类分配与重启持久化；
- migrated legacy Basic Group catalogue 折叠；
- 当前 Supergroup 不消失、不退群、不被修改；
- 跨 migration date-range 旧+新历史读取；
- 旧 Session/settings 升级复用。

更早已真人验证：Telegram API 登录、Windows system proxy/Clash transport、Session 保存复用；qasync/shutdown 历史问题已有修复。

## 3. v0.1.9：Codex 本地 Telegram CLI Bridge

正式新增 `tgctl`，架构：

```text
用户
→ Codex
→ tgctl.exe
→ TelegramService
→ %APPDATA%\TelegramMultiChatExporter\telegram.session
→ Telethon user account
```

本版明确不做 MCP、daemon、24/7 listener、自动转发规则、Bot API、AI classifier、联系人/群管理、消息删除、媒体发送/媒体转发。

### CLI 入口

开发环境：

```text
python -m telegram_exporter.tgctl ...
tgctl ...
```

Windows Release：

```text
tgctl.exe
```

Portable ZIP 内也包含 `tgctl.exe`。

### 正式命令

```text
tgctl status
tgctl chats list
tgctl messages search
tgctl messages get
tgctl forward
tgctl send
```

核心命令支持 `--json`：

```json
{"ok":true,"data":{}}
{"ok":false,"error":{"code":"...","message":"...","details":{}}}
```

稳定错误码包括：

`NOT_AUTHORIZED / CHAT_NOT_FOUND / AMBIGUOUS_CHAT / MESSAGE_NOT_FOUND / FLOOD_WAIT / WRITE_FAILED / INVALID_ARGUMENT / SESSION_BUSY`

## 4. Session / 登录 / 并发规则

- 继续复用 `%APPDATA%\TelegramMultiChatExporter\api_credentials.json`；
- 继续复用 `%APPDATA%\TelegramMultiChatExporter\telegram.session`；
- 复用现有 Windows system proxy detection；
- tgctl 不重新实现 phone / OTP / 2FA 登录；未授权时提示先打开 GUI 登录；
- GUI 与 tgctl 对同一 Telethon SQLiteSession 使用 OS-level `SessionLease`；
- GUI 已占用 Session 时 tgctl 应返回 `SESSION_BUSY`，反向同理；
- 第一版不允许两个独立进程同时打开同一 Telethon SQLiteSession。

未来若做 MCP，应优先升级为单一后台 Telegram daemon 持有 Session，GUI / tgctl / MCP 通过 IPC 调用。

## 5. Read operations

- `status`：安全账号状态，只输出 user id/display name/username、安全 Session 标签、proxy 标签；不得输出 phone/api_hash/OTP/2FA/session contents。
- `chats list`：复用 `list_groups()`、Telegram Chat Folder membership 和 migrated-group collapse；支持 `--folder / --search / --limit`。
- `messages search`：支持 chat、contains、since、until、limit、`--case-sensitive`；只读取 text/caption，不下载聊天媒体。
- `messages get`：按 ids 精确获取；缺失 id 返回 `MESSAGE_NOT_FOUND`。
- chat reference 支持 marked chat_id、精确 @username、精确 title；同名 title 返回 `AMBIGUOUS_CHAT` 候选，不得静默 first-match。

## 6. Write operations 与安全边界

- `forward` 使用 Telethon 真正 `forward_messages`，支持 `--to me` Saved Messages；不是复制正文再 send。
- 第一版 forward 只支持本项目允许的 text/caption 范围；媒体消息不得因为加入 CLI 而扩成媒体转发功能。
- `send` 只发送纯文本，`parse_mode=None`。
- forward/send 都支持 `--dry-run`。
- forward 默认最多 20 条；显式 `--allow-large-batch` 后 hard cap 200 条；超过必须拒绝。
- FloodWait 返回结构化 `FLOOD_WAIT` + `retry_after_seconds`；不得自动疯狂重试。
- 写日志只记录动作类型、chat/message id、数量、结果、text length；不得记录消息正文。
- 未来 Agent 不得为了“方便 Codex”绕过 dry-run、批量上限、chat ambiguity、FloodWait 或 Session lock。

## 7. CI / 打包状态

PR #16 和正式 Release CI 均全绿。

Release workflow `33258806323` 已通过：

- pytest；
- GUI + tgctl import check；
- GUI one-file build；
- GUI portable onedir build；
- standalone `tgctl.exe` build；
- one-file GUI smoke-test；
- portable GUI smoke-test；
- standalone tgctl smoke-test；
- portable 内 tgctl smoke-test；
- SHA256SUMS；
- GitHub Release 创建与资产上传。

## 8. v0.1.9 仍待真人 Telegram E2E

CI/mock 不能替代以下真实账号验证：

1. 关闭 GUI 后 `tgctl status --json` 直接复用已有 Session，无 phone/OTP/2FA；
2. `chats list --folder` 与真实 Telegram folder 基本一致；
3. `messages search/get` 返回真实 chat text/caption；
4. forward dry-run 到 `me` 不产生 Telegram 写入；
5. 用户确认后真实 forward 到 Saved Messages；
6. send dry-run 不写入；
7. 用户确认后真实 send 到 Saved Messages；
8. GUI 已打开时 tgctl 返回 `SESSION_BUSY`，反向同理；
9. FloodWait 真实发生时不自动循环重试；不要为了 E2E 故意制造 FloodWait。

真实写操作不要自行向陌生人/陌生群测试；Saved Messages 优先。

## 9. 三种“分组/分类”继续严格区分

- Telegram Chat Folder：账号同步，只读筛选；
- Focused workspace：GUI 工作群；
- Export Category：本地 JSON 路径分类。

`tgctl chats list --folder` 只读取第一种，不写回 Telegram，也不影响 Export Category。

## 10. 下一阶段 MCP 方向

推荐：

```text
single Telegram daemon (owns session)
├─ GUI IPC client
├─ tgctl IPC client
└─ MCP IPC client
```

还需要：

- IPC protocol；
- daemon lifecycle / crash recovery；
- 本机客户端鉴权；
- MCP tool schema；
- write confirmation policy；
- 将 GUI / tgctl 从直接持有 SQLiteSession 迁移为 IPC client。

在这些完成前，不要让 GUI / tgctl / MCP 三个进程各自打开同一 SQLiteSession。
