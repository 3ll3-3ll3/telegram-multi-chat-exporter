# Design Decisions Index

本文件保留项目历史决策的**压缩索引**。长期架构/安全决策优先放在 [`docs/decisions/`](decisions/) ADR 中。若用户明确改变方向，应修改对应 ADR/条目并同步 `HANDOFF.md`。

## GUI / export foundations

### D-001 — 独立导出文件，不做累计归档
Accepted. 输出 `总输出目录 / Export Category / 群组 / YYYY-MM-DD_HH-mm-ss.json`；历史 JSON 不读取、不合并、不回写，同秒 `_2/_3/...`。

### D-002 — JSON 是 GUI 导出的权威数据源
Accepted. 若未来加入 HTML，只从已有 JSON 本地渲染，不重新抓 Telegram。

### D-003 — GUI 消息文本优先，不下载聊天媒体
Accepted. Caption 可保留；群资料头像只作为 selector UI cache。

### D-004 — 每群规则独立
Accepted. Date range / current unread / since-last + Export Category 均按群独立。

### D-005 — Focused workspace
Accepted. 完整 catalogue 与主工作区分离；主表只显示用户主动选择的工作群。

### D-006 — Current unread 使用冻结边界
Accepted. 导出只处理开始时冻结范围，运行中新消息不纳入本次。

### D-007 — Option B read acknowledgement
Accepted. 默认 OFF；固定 `JSON atomic success → checkpoint → optional read ack`。

### D-008 — qasync 单事件循环 + 非阻塞 Dialog
Accepted. Qt + Telethon 共用 qasync；不重新引入 nested blocking modal。

### D-009 — Windows system proxy 显式传给 Telethon
Accepted. GUI/CLI/Core 复用同一 proxy detection。

### D-010 — Telegram Desktop 兼容限定在文本范围
Accepted. 不为兼容扩成完整媒体备份。

### D-011 — 正式二进制只通过 GitHub Releases 分发
Accepted. Actions Artifact 仅用于 CI/Candidate。

### D-012 — 本地状态最小化
Accepted. Checkpoint/settings/job metadata 不保存聊天正文；正文输出/导出是用户明确动作。

### D-013 — 杀软误报/代码签名当前非主线
Accepted / user-deprioritized. 除非用户重新提高优先级，不投入主开发时间。

### D-014 — Telegram Chat Folders 只读复用
Accepted. 用于筛选 catalogue，不写回 Telegram。

### D-015 — 品牌 TG Exporter，但 AppData 路径保持兼容
Accepted. 展示 `TG Exporter / TG 导出器`，包名 `telegram_exporter`；路径继续 `%APPDATA%\TelegramMultiChatExporter\`。

### D-016 — 群头像按需加载
Accepted. Placeholder + 可见项 lazy load + bounded concurrency + AppData cache；失败不阻断。

### D-017 — Export Category 由软件管理
Accepted. 本地创建/持久化/自动建目录；删除分类不删除历史磁盘数据。

### D-018 — Basic Group → Supergroup 只显示一个 logical chat
Accepted. Current Supergroup 为主实体，legacy peer 只用于历史；不按同名猜 migration。

完整长期理由：[`ADR-005`](decisions/005-migrated-group-logical-identity.md)。

## tgctl v0.1.x

### D-019 — 先做本地 tgctl，而不是直接做 MCP
Accepted. 先稳定 deterministic Core/CLI/write safety；MCP 未来只应成为薄 adapter。

### D-020 — tgctl 复用 GUI 已登录 Session，不做第二套登录
Accepted. 复用 AppData credentials/session/proxy；未授权提示先 GUI 登录；phone/OTP/2FA 不进 CLI。

### D-021 — v0.1.x direct GUI/tgctl 不能并发打开 SQLiteSession
Accepted compatibility rule. 使用 OS `SessionLease`；禁止绕锁/复制 Session。v0.2+ 通过 daemon 解决共存，而不是删除安全锁。

### D-022 — tgctl 使用稳定 JSON envelope/error code
Accepted. Codex 解析结构化协议，不解析自然语言日志。GUI export JSON 与 tgctl protocol 是两个不同 schema。

### D-023 — Telegram writes 使用 dry-run + caps + no ambiguity
Accepted. Forward/send dry-run；forward 20/200；AMBIGUOUS_CHAT；FloodWait structured stop；no body logging。

### D-024 — Forward 必须是真正 Telegram forward
Accepted. 不能静默复制正文 + send；当前范围不扩成媒体转发器。

### D-025 — Send 只做纯文本
Accepted. `parse_mode=None`；不扩成联系人/群管理或媒体发送。

完整长期 write policy：[`ADR-004`](decisions/004-telegram-write-safety-and-no-auto-retry.md)。

## v0.2 / v0.3 accepted architecture

历史上 D-026 曾写成 “future MCP daemon direction”。该方向已经在 v0.2/v0.3 Candidate 实现，因此现状更新如下：

### D-026 — Single local Telegram daemon
Accepted / implemented in Candidate. Daemon 是唯一 Session/TelegramClient owner；GUI/tgctl 走 IPC；future MCP 只能作为同一 Core 的 adapter。

ADR：[`001-single-daemon-session-owner.md`](decisions/001-single-daemon-session-owner.md)。

### D-027 — Windows Named Pipe + authenticated UTF-8 JSON bytes
Accepted / implemented in Candidate. 不开 TCP/HTTP；禁止 pickle transport。

ADR：[`002-local-named-pipe-json-ipc.md`](decisions/002-local-named-pipe-json-ipc.md)。

### D-028 — Export 独占 Telegram work；reader 等待；real write 拒绝
Accepted. 这是可预测性优先的用户体验选择；不在 export 后偷偷执行 queued writes。

见 ADR-001 / ADR-004。

### D-029 — GUI 关闭/崩溃不能终止 daemon-side export
Accepted. Export 在 daemon 内执行；GUI 重开读取安全 job metadata。Daemon 自己崩溃可标 interrupted，但不伪报完成。

### D-030 — Daemon 按需启动、tray 可见、idle exit
Accepted. 不注册 Windows Service/开机常驻；无 GUI/job/request 后约 10 分钟退出。

### D-031 — 登录交互只属于 GUI
Accepted. Tgctl/Codex 不收集 phone/OTP/2FA。

### D-032 — Write transport unknown outcome 不自动 retry
Accepted. Read-only 可有限恢复；write submit 后断线返回 `WRITE_OUTCOME_UNKNOWN`，先检查目标聊天。

ADR：[`004-telegram-write-safety-and-no-auto-retry.md`](decisions/004-telegram-write-safety-and-no-auto-retry.md)。

## v0.3 Personal Account Reader

### D-033 — v0.3 继承 v0.2 daemon，不另起 direct-session reader
Accepted.

### D-034 — Reader 使用独立全账号模型
Accepted. Private/Bot/Saved/Forum 不机械塞入 GUI `GroupInfo`。

### D-035 — 所有大范围 reader bounded pagination
Accepted. Default 100 / max 500；opaque HMAC/query-bound cursor；不带 access_hash/file_reference。

### D-036 — Stable dialog order + message-id continuation
Accepted. Migration history使用 current→legacy composite segment；消息身份 `(source_chat_id,message_id)`。

ADR：[`003-bounded-reader-pagination-and-safe-cursors.md`](decisions/003-bounded-reader-pagination-and-safe-cursors.md)。

### D-037 — Sender role 是查询时 current snapshot
Accepted. 不伪造历史管理员任期；unknown 不当成 member。

### D-038 — Anonymous admin/send-as 不反推隐藏个人
Accepted. 只表达 Telegram 可以证明的 identity。

### D-039 — Rich metadata 可读，media 默认 metadata-only
Accepted. Explicit media download 必须 plan→confirmation token→download + bounded hard caps + atomic file finalization。

### D-040 — v0.3 GUI 与 v0.3 tgctl 正常不互相 SESSION_BUSY
Accepted. Same-generation clients 共用 daemon；SESSION_BUSY 只用于 legacy/direct holder compatibility。

### D-041 — 查不到消息不等于“已删除”
Accepted. 统一 `not_found_or_unavailable`，不伪造 deleted=true。

### D-042 — URL domain 必须解析真实 hostname
Accepted. Exact/subdomain match；reject lookalike suffix；不访问 URL、不 follow redirect。

### D-043 — v0.3 Candidate 完成后先真人 E2E，不自动 Release
Accepted. Candidate frozen + hash traceable；human E2E PASS + explicit user release authorization 才能 merge/release。

ADR：[`006-human-e2e-release-gate.md`](decisions/006-human-e2e-release-gate.md)。

## ADR quick index

| ADR | Decision |
| --- | --- |
| [ADR-001](decisions/001-single-daemon-session-owner.md) | Single daemon is the only Telegram Session owner |
| [ADR-002](decisions/002-local-named-pipe-json-ipc.md) | Local authenticated Named Pipe + UTF-8 JSON bytes |
| [ADR-003](decisions/003-bounded-reader-pagination-and-safe-cursors.md) | Bounded reader pages + HMAC/query-bound cursors |
| [ADR-004](decisions/004-telegram-write-safety-and-no-auto-retry.md) | Explicit/bounded writes; no automatic replay after unknown outcome |
| [ADR-005](decisions/005-migrated-group-logical-identity.md) | Current Supergroup is the logical chat; legacy is historical source |
| [ADR-006](decisions/006-human-e2e-release-gate.md) | v0.3 requires human E2E + explicit release authorization |

## Updating decisions

若用户改变上述长期方向：

1. 修改/新增 ADR，明确 superseded decision；
2. 更新本索引；
3. 更新 `HANDOFF.md` 的 Current State / Recent Decisions / Risks；
4. 若影响安全/Production，同步 `SECURITY_MODEL.md`；
5. 若影响 runtime，按 `TESTING.md` 与 release gate 重验。