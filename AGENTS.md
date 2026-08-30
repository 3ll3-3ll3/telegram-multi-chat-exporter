# AGENTS.md

本文件是任何后续 Agent / Codex / 自动化开发者进入本仓库后的**第一阅读入口**。除非用户明确改变产品方向，否则以下规则视为长期不变量。

## 1. 阅读顺序

1. `AGENTS.md`
2. `HANDOFF.md`
3. `docs/PERSONAL_ACCOUNT_READER_V3_DESIGN.md`
4. `docs/ARCHITECTURE.md`
5. `docs/DECISIONS.md`
6. `docs/TESTING.md`
7. `SECURITY.md`
8. `docs/CODEX_TGCTL.md`
9. 涉及 GUI JSON 时读 `docs/JSON_COMPATIBILITY.md`

不要只凭 README 推断实现状态；`HANDOFF.md` 才是当前交接快照。

## 2. 版本/代际

```text
第一代 v0.1.x = GUI exporter + direct-session tgctl
第二代 v0.2.0 = single daemon + local Named Pipe IPC
第三代 v0.3.0 = v0.2 daemon + Personal Account Reader
```

当前正式 Release 仍是 v0.1.10。`codex/personal-account-reader-v0.3.0` 是 candidate 开发线；未经用户真实账号验收与明确授权，不创建 v0.3.0 Release。

## 3. v0.3 进程所有权

必须保持：

```text
TG daemon（唯一 Telegram Session / Telethon owner）
├─ TG Exporter GUI IPC client
├─ tgctl IPC client
└─ future MCP client（v0.3 不实现）
```

规则：

- 只有 daemon 可以创建 `TelegramClient`、打开 `%APPDATA%\TelegramMultiChatExporter\telegram.session`、获取 `SessionLease`。
- GUI/tgctl 不得 fallback direct SQLiteSession，不复制 Session，不创建隐藏第二 Session。
- IPC 继续使用 Windows Named Pipe / `AF_PIPE` + UTF-8 JSON bytes；禁止 pickle transport；不开 TCP/HTTP。
- v0.3 GUI 与 v0.3 tgctl 正常可同时使用，不应产生旧版 GUI↔tgctl `SESSION_BUSY`。
- `SESSION_BUSY` 仅用于 legacy/direct process 已 OS-lock Session 的兼容边界；packaged native exit code 必须是 8。
- 登录 phone/OTP/2FA 仍只在 GUI；tgctl/Codex 不实现登录交互。

## 4. 第二代桌面体验不得回退

用户已确定：

- 关闭 GUI 时正在导出的 job 继续后台完成；
- GUI 没开时 tgctl/Codex 可自动唤醒 daemon；
- export 活跃时 Telegram reader 等待，不和 export 抢同一个 Telegram client；
- export 活跃时真实 send/forward 立即 `EXPORT_IN_PROGRESS`，不得排队后偷偷发送；
- GUI 崩溃后 daemon/job 继续，GUI 重开可恢复任务状态；
- daemon 有 Windows 托盘；
- phone/OTP/2FA 仅 GUI；
- 无 GUI lease、无 job、无请求后约 10 分钟 idle exit。

## 5. GUI 导出不变量

- 每群每次导出独立 JSON；历史 JSON 不读取、不合并、不覆盖。
- 输出：`总输出目录 / Export Category / 群组 / YYYY-MM-DD_HH-mm-ss.json`，同秒冲突 `_2/_3/...`。
- Export Category 是本地分类，不是 Telegram Chat Folder。
- 每群独立 date range / current unread / since last successful export。
- 默认聊天导出只保留文字/caption，不下载聊天媒体；群头像仅 UI cache 例外。
- Basic Group→Supergroup 只显示当前逻辑群；date-range/history 可按 Telegram 显式 migration 关系读取 legacy + current。
- **current unread 必须在每个群真正开始执行导出时单独冻结边界**：`read_inbox_max_id_at_group_start < id <= latest_message_id_at_group_start`。不得继续使用 catalogue refresh 时的旧 snapshot，也不得移除 upper bound；snapshot 之后新到消息不属于本次导出，也不得被本次 optional read-ack 标已读。
- migrated 群的 current unread 只对当前 logical Supergroup 抓 snapshot；legacy Basic Group 只用于历史兼容，不参与 current unread。
- GUI Option B “导出后标已读”默认 OFF；严格 `JSON atomic success → checkpoint → optional read ack`，且 read-ack 必须使用与本次导出完全相同的 frozen snapshot upper bound。
- qasync async flow 不重新引入 `QDialog.exec()` 或其它 nested blocking modal。

## 6. v0.3 Reader 安全边界

新增 reader 默认 Telegram read-only：

```text
account.get
dialogs.list
chats.get
chats.members
messages.history
messages.search
messages.get
topics.list
topics.history
media metadata
```

读取不得：发送、转发、删除、退群、改 Chat Folder、标已读、自动下载媒体。

`media download` 是用户显式请求的**本地磁盘写入**，不是默认 reader 行为。必须两阶段：plan → confirmation token → download；普通 20 files / 500 MiB，显式 large 后硬上限 200 files / 5 GiB；`.part` 成功后原子 rename。

现有 Telegram 写能力仅有已批准的 `send` / `forward` / GUI optional read-ack，不因 reader 扩展而放宽。

## 7. Reader 模型与分页

不要把 private/bot/Saved Messages 机械塞进 GUI `GroupInfo`。Reader 使用独立：

```text
AccountProfile
DialogInfo
ChatDetails
ParticipantInfo
SenderInfo
MessageInfoV3
ForumTopicInfo
MediaMetadata
Page
```

分页：默认 100、max 500；全历史禁止无界 `limit=None`。Cursor 必须 opaque/HMAC/query-bound，不含 `access_hash` / `file_reference` / Session secret。

Dialogs completeness 默认 canonical stable order；history newest→older 用 message id 继续。迁移群逻辑历史唯一键是 `(source_chat_id, message_id)`，不能只按 message id 去重。

## 8. 身份真实性

- owner/admin/member 来自 Telegram participant/admin data，不从显示名猜。
- `sender-role` 是查询时当前角色 snapshot，不伪造历史管理员任期。
- 匿名管理员/send-as 不得根据 `post_author`、显示名或管理员表反推具体 user id。
- 权限不足必须返回 `MEMBERS_UNAVAILABLE` / `ACCESS_DENIED` 或 unknown，不拿消息作者集合冒充完整成员表。
- `--url-domain` 必须解析真实 hostname；`mypikpak.com.evil.com` 不得匹配 `mypikpak.com`。

## 9. MessageInfoV3

history/search/get/topic history 尽量统一安全 schema：chat/source chat/message id、date/edit_date、结构化 sender、text/caption、entities、reply、forum topic、forward origin、grouped id、views/forwards、reactions、poll、service action、pinned、media metadata、availability。

Telegram 查不到消息时只能说 `MESSAGE_NOT_FOUND/not_found_or_unavailable`，不能自动声称“已删除”。

## 10. tgctl 兼容与写安全

旧命令继续兼容：

```text
status
chats list
messages search
messages get
forward
send
```

- `messages search` 默认第三代 rich/paged 行为，必要时保留 `--legacy-schema` 过渡。
- `forward` 必须是真正 Telegram forward，不静默复制正文+send。
- send 仍为纯文本。
- forward/send 保留 `--dry-run`；默认 20，显式大批量最多 200。
- FloodWait 不 retry storm；返回 `retry_after_seconds`。
- 同名 dialog 必须 `AMBIGUOUS_CHAT` + safe candidates。
- write 请求已发送但返回中断时不得自动 retry，返回 `WRITE_OUTCOME_UNKNOWN`。

## 11. Secret / stdout / 日志

严禁提交、stdout、日志、cursor、异常 repr 泄露：

- `api_id/api_hash`；
- phone / OTP / 2FA；
- Session 内容；
- credentials 原文；
- Telegram `access_hash`；
- `file_reference` bytes；
- IPC auth secret；
- 真实头像 cache / 本地导出内容。

用户明确执行 messages/history/search/get 时，正文可出现在 stdout JSON/JSONL；普通 `app.log` 不得记录正文、caption、URL 文本或媒体文件名。写操作日志只记 action、safe IDs、数量、耗时/结果。

## 12. 明确非目标

除非用户重新明确要求并重新评估安全设计，不做：Secret Chat、已删除内容恢复、绕权读取、Bot API、24/7 Telegram listener、自动转发规则、AI 自动分类、联系人/群/管理员管理、删除消息、退群、修改 Chat Folder、媒体发送/媒体转发、MCP Server、Web/TCP 服务。

## 13. CI / Candidate / Release

v0.3 candidate 至少要求：

```text
pytest -q
GUI + daemon + reader + CLI import check
TGExporter PyInstaller one-file build
TGExporter PyInstaller portable onedir build
tgctl PyInstaller one-file build
standalone + portable packaged SESSION_BUSY JSON/native exit 8 regression
one-file + portable GUI smoke
standalone + portable tgctl smoke
candidate SHA-256 + Actions artifact
```

还必须覆盖 unread export-start snapshot、cursor、dialogs types、owner/admin/anonymous sender、rich message、Forum、URL domain、Saved Messages、JSONL、media confirmation/limits、敏感信息泄漏。

Mock/CI 不能代替真实账号只读 E2E。完成 candidate 后停止，不发布 Release，等待用户验收。

## 14. 交接纪律

任何用户可见功能、关键 bug、架构、安全策略、candidate/Release 或真人 E2E 状态变化后更新 `HANDOFF.md`；长期不可逆决策同步 `docs/DECISIONS.md`。交接必须明确：正式最新版、开发 head、CI 状态、哪些真人验证、哪些仅 mock、未完成事项和下一步。
