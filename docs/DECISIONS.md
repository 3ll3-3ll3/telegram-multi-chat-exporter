# Design Decisions

本文件记录已经明确采用、后续 Agent 不应随意反转的设计决策。若用户明确改变方向，应修改对应条目并在 `HANDOFF.md` 记录。

## D-001：独立导出文件，不做累计归档
**Accepted** — `总输出目录 / 导出分类 / 群组 / YYYY-MM-DD_HH-mm-ss.json`；历史 JSON 不读取、不合并、不回写，同秒冲突 `_2/_3/...`。

## D-002：JSON 是 GUI 导出的权威数据源
**Accepted** — HTML 如未来加入，只从既有 JSON 本地渲染，不重新抓 Telegram。

## D-003：聊天消息文本优先，不下载媒体
**Accepted** — GUI 导出不下载聊天媒体；caption 可保留。群资料头像仅为 selector UI cache。

## D-004：每群规则完全独立
**Accepted** — date range / current unread / since last export + Export Category 均按群独立。

## D-005：Focused workspace
**Accepted** — catalogue 与主工作区分离，主表只显示用户选择的工作群。

## D-006：未读使用冻结快照
**Accepted** — `read_inbox_max_id < id <= latest_message_id_at_refresh`。

## D-007：Option B 已读策略
**Accepted** — 默认 OFF；JSON success → checkpoint → optional read ack。

## D-008：qasync 单事件循环 + 非阻塞 Dialog
**Accepted** — Qt + Telethon 共享 qasync，不重新引入 nested modal loop。

## D-009：Windows 系统代理显式传给 Telethon
**Accepted** — GUI/CLI 都复用 `proxy.py`。

## D-010：Telegram Desktop 兼容为“文本范围内尽量一致”
**Accepted** — 不为兼容而扩成完整媒体备份。

## D-011：正式二进制只通过 GitHub Releases 分发
**Accepted** — Actions Artifact 仅 CI 临时产物。

## D-012：本地状态最小化
**Accepted** — `local_state.json` 只保存 checkpoint；settings 保存 UI 配置，不保存正文。

## D-013：杀软误报/代码签名暂不作为主线
**Accepted (user-deprioritized)**。

## D-014：优先复用 Telegram 账号 Chat Folders
**Accepted** — Dialog Filters 只读筛选 catalogue，不写回 Telegram。

## D-015：品牌为 TG Exporter
**Accepted** — 展示名 `TG Exporter / TG 导出器`，内部包仍 `telegram_exporter`；兼容数据目录继续 `%APPDATA%\TelegramMultiChatExporter\`。

## D-016：选择器头像按需加载
**Accepted** — 首字占位、可见项加载、受限并发、AppData cache，失败不阻断。

## D-017：Export Category 由软件自己管理
**Accepted** — 分类本地创建/持久化/自动建目录；删除分类不删历史磁盘数据。

## D-018：Basic Group → Supergroup 只显示一个逻辑群
**Accepted** — 当前 Supergroup 为主实体，legacy peer 仅用于历史兼容；不按同名猜 migration。

## D-019：增加本地 tgctl，而不是直接做 MCP

**状态：Accepted（v0.1.9）**

用户要求先实现最初级但真正可用的“Codex 手动操控 Telegram”：

```text
Codex → local tgctl → TelegramService → Telethon user session
```

本阶段不做 MCP、Web Server、长期监听、规则引擎、AI Agent 或 Bot API。

理由：先把确定性 Telegram Core / CLI protocol / write safety 做稳定，未来 MCP 可以薄薄建立在相同 service abstraction 之上，而不是同时调试协议、后台生命周期和 Telegram 业务。

## D-020：tgctl 必须复用 GUI 已登录 Session，不实现第二套登录

**状态：Accepted（v0.1.9）**

继续复用：

```text
%APPDATA%\TelegramMultiChatExporter\api_credentials.json
%APPDATA%\TelegramMultiChatExporter\telegram.session
```

以及现有 Windows system proxy detection。

已有 Session 时 tgctl 不再输入 phone/OTP/2FA；未授权返回 `NOT_AUTHORIZED` 并提示先打开 GUI 登录。

理由：用户要的是 Codex 调用已经登录的个人账号，不是再造 Telegram 登录客户端。

## D-021：GUI 与 tgctl 不并发打开同一 SQLiteSession

**状态：Accepted（v0.1.9）**

Telethon 默认 Session 为 SQLite。第一版使用 OS-level `SessionLease` 保证同一个本地 Session 同时只有一个 TG Exporter/tgctl 进程拥有。

冲突：

```text
GUI already owns → tgctl SESSION_BUSY
tgctl already owns → GUI SessionBusyError
```

禁止绕过 lock 或复制 Session 来“支持并发”。未来 GUI/CLI/MCP 并发时应改为 single daemon owns Session + IPC。

## D-022：tgctl 使用稳定 JSON envelope / error code

**状态：Accepted（v0.1.9）**

核心命令支持 `--json`，stdout 只输出：

```json
{"ok":true,"data":{}}
{"ok":false,"error":{"code":"...","message":"...","details":{}}}
```

错误码和非零退出码是 Codex 判断状态的正式接口，不能要求 Codex解析自然语言日志。

GUI Telegram Desktop-style export JSON 与 tgctl RPC-like JSON 是两个不同协议，不要混为一谈。

## D-023：tgctl 写操作采用 dry-run + 硬批量限制 + 无歧义目标

**状态：Accepted（v0.1.9）**

read commands 可以直接执行；write commands 当前只有 `forward` 和 `send`。

安全边界：

- forward/send 支持 `--dry-run`；
- forward 默认最多 20 条；显式 `--allow-large-batch` 后最多 200 条 hard cap；
- 同名 chat 返回 `AMBIGUOUS_CHAT`，不 first-match；
- FloodWait 返回等待秒数，不自动 retry storm；
- write 日志不记录正文。

这些边界是 Codex automation 的核心安全层，未来 Agent 不得为了“更自动”擅自移除。

## D-024：第一版 forward 必须是真正 Telegram forward，但不扩成媒体转发器

**状态：Accepted（v0.1.9）**

`tgctl forward` 使用 Telethon `forward_messages`，不能退化为复制正文 + `send_message`。

同时用户明确本版不做图片/视频/文件转发，因此 preflight 只允许纯文本消息和普通网页 preview；媒体消息 id 进入 `failed_ids`。

## D-025：第一版 tgctl send 只做纯文本

**状态：Accepted（v0.1.9）**

`send_text_message` 使用 `parse_mode=None`，不发送图片/文件/语音，不做联系人/群管理等副作用。

## D-026：未来 MCP 优先基于 single local daemon

**状态：Future direction**

若升级 MCP，推荐：

```text
single Telegram daemon owns Session
├─ GUI IPC
├─ tgctl IPC
└─ MCP IPC
```

需要 IPC、daemon lifecycle/crash recovery、本机客户端鉴权、MCP tool schema 与 write confirmation policy；当前 v0.1.9 不实现。
