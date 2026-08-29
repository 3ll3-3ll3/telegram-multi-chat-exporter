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
**Accepted（v0.1.9）** — `Codex → local tgctl → TelegramService → Telethon user session`。先稳定确定性 Core/CLI，再考虑 MCP。

## D-020：tgctl 必须复用 GUI 已登录 Session，不实现第二套登录
**Accepted（v0.1.9）** — 复用 `%APPDATA%\TelegramMultiChatExporter\api_credentials.json`、`telegram.session` 与 Windows system proxy。未授权返回 `NOT_AUTHORIZED`。

## D-021：v0.1.9 GUI 与 tgctl 不并发打开同一 SQLiteSession
**Accepted（v0.1.9 compatibility）** — 使用 OS-level `SessionLease`；不得复制 Session 或绕过锁。v0.2.0 起 Session owner 将迁移到 daemon，但旧 v0.1.9 进程仍受此锁保护。

## D-022：tgctl 使用稳定 JSON envelope / error code
**Accepted（v0.1.9+）** — `{"ok":true,"data":...}` / `{"ok":false,"error":...}` 是 Codex 正式接口，不能要求解析自然语言日志。

## D-023：tgctl 写操作采用 dry-run + 硬批量限制 + 无歧义目标
**Accepted（v0.1.9+）** — forward/send 保留 dry-run；forward 默认 20、显式 large batch 后 hard cap 200；AMBIGUOUS_CHAT 不静默选择；FloodWait 不 retry storm；write log 不记正文。

## D-024：forward 必须是真正 Telegram forward，但不扩成媒体转发器
**Accepted（v0.1.9+）** — 使用 Telethon `forward_messages`；第一阶段仍限制 text/普通网页 preview，媒体不扩功能。

## D-025：tgctl send 只做纯文本
**Accepted（v0.1.9+）** — `parse_mode=None`，不发送媒体、不做联系人/群管理等额外副作用。

## D-026：v0.2.0 采用 single local Telegram daemon
**Accepted（2026-08-29）**。

迁移目标：

```text
TG daemon 唯一持有 TelegramService / Telethon / telegram.session
├─ GUI IPC client
├─ tgctl IPC client
└─ future MCP IPC client
```

GUI/tgctl 迁移完成后不得直接创建 TelegramClient，也不得在 daemon 不可用时偷偷回退 direct SQLiteSession。

## D-027：本地 IPC 使用 Windows Named Pipe + JSON bytes
**Accepted（v0.2.0）**。

优先 `multiprocessing.connection` + `AF_PIPE`；认证使用本地随机 auth secret；传输只用 `send_bytes/recv_bytes` 的 UTF-8 JSON，禁止 pickle object transport。不开 TCP/HTTP/Web Server。

## D-028：导出是独占 Telegram job；读取等待；真实写入拒绝
**Accepted（用户体验选择 3B/4B）**。

- export batch 活跃时，`messages.search/get`、`chats.list`、avatar 等 Telegram read 等待 export 完成；
- daemon/job/status/heartbeat 等纯本地 RPC 始终可用；
- export 活跃时真正 `send/forward` 立即返回 `EXPORT_IN_PROGRESS`，不得排队后自动发送；
- dry-run 不产生写入，但若需要 Telegram preflight，则按 read 等待 export 完成；
- 无 export 时 write 仍串行并再次执行所有安全检查。

理由：用户更看重可预测和稳定，而不是导出期间 Telegram 操作并发。

## D-029：GUI 关闭或崩溃不能终止 daemon-side export job
**Accepted（用户体验选择 1B/5B）**。

导出在 daemon 内执行并直接原子写 JSON。GUI 正常关闭或崩溃后 job 继续；GUI 重开通过 job registry 恢复进度/结果。daemon 自己崩溃后不承诺自动续跑同一个 Telegram job，但必须把安全 metadata 标记 interrupted，不能伪报成功。

Option B 顺序继续是：`JSON success → checkpoint → optional read ack`，由 daemon coordinator 单进程保证。

## D-030：daemon 按需启动、托盘可见、空闲自动退出
**Accepted（用户体验选择 2A/6B/8B）**。

- GUI/tgctl 可自动 `ensure_running()`；
- 不注册 Windows Service、不设开机自启；
- daemon 在交互式 Windows 会话显示托盘图标，可看连接/导出/空闲状态、打开 TG Exporter、请求退出；
- 有 export job 时手动退出不得粗暴杀任务，优先“导出完成后退出”；
- GUI 通过 lease/heartbeat 表示仍在使用；GUI 崩溃 lease 自动过期；
- 无 GUI lease、无请求、无 job、无排队 read 后约 10 分钟退出；下次调用自动唤醒。

## D-031：登录交互仍只属于 GUI
**Accepted（用户体验选择 7A）**。

手机号、OTP、2FA 只能由 TG Exporter GUI 收集。为了让 daemon 唯一拥有 Telethon，GUI 通过仅允许 `client.kind=gui` 的 auth RPC 调用 daemon；tgctl/Codex 调 auth RPC 必须得到 `AUTH_GUI_ONLY`。OTP/2FA 不持久化、不日志记录。

## D-032：write transport failure 不自动重试
**Accepted（v0.2.0）**。

read-only RPC 在 daemon/pipe 故障后最多自动恢复并重试一次；真实 send/forward 在请求已交给 daemon 后如果连接中断，客户端返回 `WRITE_OUTCOME_UNKNOWN`，必须先检查目标聊天，绝不自动 retry 造成重复消息。

详细设计见 `docs/DAEMON_IPC_DESIGN.md`。
