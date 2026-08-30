# Architecture

本文件同时描述当前正式 Production（v0.1.10）与第三代 Candidate（v0.3.0）。实时状态以 `HANDOFF.md` 为准。

## 1. Product shape

TG Exporter 有两个长期入口：

- `TGExporter.exe`：Windows GUI，多群独立文本 JSON 导出；
- `tgctl.exe`：面向 Codex/命令行的稳定机器接口。

项目不使用 Telegram Bot API；它通过用户自己的 Telethon Session 访问用户账号已有权限。

## 2. Production v0.1.10 architecture

```text
TGExporter GUI ─┐
                ├→ TelegramService → Telethon → telegram.session → Telegram
 tgctl.exe     ─┘
```

GUI 和 tgctl 是两个 direct-session 入口。Telethon 默认 SQLiteSession 不应被多个进程并发打开，因此 `TelegramService` 使用 OS `SessionLease`：

- 同时只能有一个 direct owner；
- 后启动者安全返回 `SESSION_BUSY`；
- packaged `tgctl` native exit code 契约为 8；
- 不复制 Session、不删锁绕过。

v0.1.10 的这套行为是正式兼容线，即使 v0.3 Candidate 已有不同进程模型，也不要把未发布行为倒写进 Production。

## 3. Candidate v0.3.0 architecture

第三代继承 v0.2 single-daemon：

```text
TGExporter GUI ─┐
                ├→ authenticated local IPC → TG daemon → TelegramService/Telethon → one user Session
 tgctl / Codex ─┘
```

Daemon 是唯一 `TelegramClient` / Session owner。GUI/tgctl 迁移为 IPC clients，不能在 daemon 不可用时 fallback direct Session。

ADR：[`001-single-daemon-session-owner.md`](decisions/001-single-daemon-session-owner.md)。

## 4. Local IPC

Candidate 使用 Windows Named Pipe / `AF_PIPE`：

- local only；
- authenticated；
- UTF-8 JSON bytes；
- `send_bytes/recv_bytes`，不用 pickle object transport；
- 不开放 TCP/HTTP/LAN；
- IPC identity/auth secret 仅本机 AppData；
- 大导出正文不通过一个巨大 IPC response 搬回 GUI。

ADR：[`002-local-named-pipe-json-ipc.md`](decisions/002-local-named-pipe-json-ipc.md)。

完整实施设计在 PR #20 分支 `docs/DAEMON_IPC_DESIGN.md`。

## 5. Daemon lifecycle

v0.2/v0.3 目标体验：

- GUI/tgctl 可按需唤醒 daemon；
- daemon 在交互式 Windows 会话提供 tray 状态；
- GUI 用 lease/heartbeat 表示仍在使用；
- GUI 关闭/崩溃不终止 daemon-side active export；
- GUI 重开可读取安全 job metadata；
- 无 live GUI lease、job、request/queued read 后约 10 分钟 idle shutdown；
- tray/Explorer 异常不能使后台 worker 失败。

Daemon crash 后不承诺自动续跑同一个 Telegram export job；只能保留安全 metadata 并标 interrupted，不能伪报成功。

## 6. Operation coordination

稳定性优先，单 Telegram client 串行协调：

```text
LOCAL status/job/heartbeat       → immediate
export                           → exclusive Telegram work
reader                           → waits while export active
real send/forward during export  → EXPORT_IN_PROGRESS
confirmed media download         → bounded local-disk work, ordered through daemon policy
```

真实 write 不允许“导出结束后偷偷排队发送”。Write request 已交给 daemon 后 transport outcome unknown → `WRITE_OUTCOME_UNKNOWN`，不得自动 replay。

ADR：[`004-telegram-write-safety-and-no-auto-retry.md`](decisions/004-telegram-write-safety-and-no-auto-retry.md)。

## 7. GUI export pipeline

长期目录与数据模型：

```text
GUI GroupExportPlan
→ Telegram fetch
→ Desktop-style text serializer
→ 总输出目录/category/group/timestamp.json
→ atomic replace
→ checkpoint
→ optional read acknowledgement
```

每次/每群 JSON 独立；历史 JSON 不读取、合并或覆盖。

`Export Category` 是本地分类，Telegram Chat Folder 只是只读 catalogue filter。

消息默认不下载媒体；caption 可保留；群头像仅 UI cache。

Current-unread Option B 固定：

```text
JSON atomic success
→ checkpoint
→ optional read ack
```

## 8. Group catalogue and migration

Catalogue 与 focused GUI workspace 分开；工作区只显示用户选中的群。

Basic Group → Supergroup：current Supergroup 是 logical chat，legacy Basic Group 是 historical source。

```text
logical chat_id = current Supergroup
legacy source_chat_id = old Basic Group
unique message key = (source_chat_id, message_id)
```

不按同名推断 migration。Current-unread/since-last 使用 current；date-range/history 可 current→legacy。

ADR：[`005-migrated-group-logical-identity.md`](decisions/005-migrated-group-logical-identity.md)。

## 9. v0.3 Reader layering

Candidate 不扩大 GUI `GroupInfo`，而使用 reader-only models：

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

大体模块：

```text
TelegramService
└─ Telethon client / Session / proxy

PersonalAccountReader / V3 runtime
├─ account + dialogs
├─ dialog resolution
├─ members/current role snapshot
├─ rich history/get
├─ migrated logical identity
└─ safe serializers

reader_search.py
reader_topics.py
reader_media.py
reader_rpc.py

daemon server
└─ auth/export/write policies + reader RPC
```

完整 v0.3 设计在 PR #20 分支 `docs/PERSONAL_ACCOUNT_READER_V3_DESIGN.md`。

## 10. Dialogs / identity truthfulness

Reader dialogs 覆盖 group/supergroup/channel/private/bot/Saved Messages，以及 archive/forum/unread/pinned/muted/folder/migration safe metadata。

owner/admin/member：Telegram 当前 participant/admin snapshot；不伪造历史任期。

Anonymous admin / send-as：只返回 Telegram 可证明的 chat/channel/anonymous identity；不从显示名或 `post_author` 猜真实个人。

查不到消息是 `not_found_or_unavailable`，不自动断言 deleted。

## 11. Pagination and cursor

Reader 默认 page 100、max 500；无 hidden unbounded history。

Cursor：opaque base64url + HMAC + version/method/query fingerprint + safe continuation position。禁止包含 `access_hash` / `file_reference` / Session credentials。

Dialogs 使用 stable canonical ordering；history newest→older；migration 使用 current→legacy segment cursor。

ADR：[`003-bounded-reader-pagination-and-safe-cursors.md`](decisions/003-bounded-reader-pagination-and-safe-cursors.md)。

## 12. Advanced search / Forum

Search 支持 single/global、contains、sender ID/current role、time、message type、topic、link、URL domain、cursor。

候选扫描有 cap；达到 cap 用 cursor 继续，不无限扫描账号。

URL domain 用 hostname normalization，只匹配 exact host/真实 subdomain，不访问 URL、不 follow redirect。

Forum topic list/history 使用 Telegram/Telethon forum APIs；非 Forum 返回明确错误。

## 13. Media

普通 reader：metadata-only，不下载 `file_reference`。

显式 media download：

```text
plan
→ DOWNLOAD_CONFIRMATION_REQUIRED + HMAC token
→ no files

confirm same plan
→ enforce limits
→ safe basename
→ *.part
→ os.replace final
```

Normal 20 files/500 MiB；explicit large max 200 files/5 GiB。

## 14. Local storage

固定兼容路径：

```text
%APPDATA%\TelegramMultiChatExporter\
```

可能包含 credentials、Session、lock、settings/state、logs、avatar cache、daemon identity/job metadata。

用户导出 JSON 位于用户选择的独立 output root，不属于 AppData runtime state。

本项目没有远程生产数据库/服务器。Production 定义与信任边界见 [`SECURITY_MODEL.md`](SECURITY_MODEL.md)。

## 15. Packaging / distribution

正式 Windows 分发只通过 GitHub Releases；Candidate Actions Artifact 仅用于测试。

正式资产至少：one-file GUI、portable ZIP、standalone tgctl、SHA256SUMS。

Build/Release/Rollback 详见 [`DEPLOYMENT.md`](DEPLOYMENT.md) 和 [`RELEASE_PROCESS.md`](RELEASE_PROCESS.md)。

## 16. Release boundary for v0.3

v0.3 自动化 CI 不能替代真实 Telegram 账号 E2E。当前 Candidate 在用户 E2E PASS + 明确发布授权前保持 Draft、不 merge、不创建/覆盖 v0.3.0 Release。

ADR：[`006-human-e2e-release-gate.md`](decisions/006-human-e2e-release-gate.md)。