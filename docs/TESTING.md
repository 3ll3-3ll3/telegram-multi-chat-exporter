# Testing Guide — v0.3 Candidate

本项目测试分四层：

1. unit/mock：模型、cursor、reader/filter、daemon scheduling、GUI legacy 行为、安全边界；
2. Windows package CI：TGExporter/tgctl PyInstaller、真实 OS Session lock、native exit code；
3. Candidate artifact：one-file + portable + tgctl + SHA-256；
4. 用户真实 Telegram E2E。

**CI green 不等于真实账号 E2E。**

## 1. CI 基线

```powershell
pip install -e ".[dev]"
pytest -q
```

v0.3 Candidate gate 至少要求：

```text
pytest -q
GUI + daemon + reader + CLI import
TGExporter one-file PyInstaller
TGExporter portable onedir PyInstaller
tgctl one-file PyInstaller
standalone + portable legacy OS Session lock → packaged SESSION_BUSY JSON + native exit 8
one-file + portable GUI smoke
standalone + portable tgctl smoke
candidate SHA-256 generation
artifact upload
```

Issue #22 修复后的 frozen runtime Candidate：

```text
runtime: 7e6f62d0c12eb9f88e53a15a5daaa271ba61e68c
Windows run: 33296790070 = success
pytest: 95 passed in 2.19s
artifact: 9727721868
```

## 2. GUI/v0.2 regression

不得因 Reader 或 daemon 修改破坏：focused workspace、Telegram Chat Folder、avatar lazy load、Export Category、category/group/timestamp JSON、same-second no overwrite、migration collapse/date-range history、since-last checkpoint、Option B 顺序、qasync shutdown。

v0.3 GUI 与 v0.3 tgctl 都经 daemon，正常共存不应 `SESSION_BUSY`。export 活跃时 reader 等待；真实 send/forward 立即 `EXPORT_IN_PROGRESS`。

## 3. Current-unread export-start snapshot regression

这是 Issue #22 的长期 correctness gate，后续 Agent 不得删除或弱化。

正确语义：

```text
lower = read_inbox_max_id when this group starts execution
upper = latest_message_id when this group starts execution
export lower < id <= upper
```

必须测试：

- catalogue 中 stale snapshot 与 export-start 新状态不同 → 使用 export-start snapshot；
- upper frozen 之后到达的新消息 → 本次不导出；
- multi-group batch → 每个群轮到执行时分别 snapshot，不是 catalogue-global/batch-global；
- export 与 optional read-ack 使用同一 frozen lower/upper；
- export failure → 不 read-ack；
- JSON success + read-ack failure → JSON 保留；
- migrated Basic Group 即使存在/先枚举，也不得被 current-unread 使用；只匹配 current logical Supergroup；
- catalogue/workspace GroupInfo 不因 execution snapshot 被原地修改。

不得用“删除 upper bound”或 live-unbounded read 代替正确修复。

## 4. Cursor / page

必须覆盖：default 100/max 500、HMAC sign/verify、method/query mismatch、tamper、不含 access_hash/file_reference/credential、dialogs stable pagination、history 2+ pages no overlap/gap、migration current→legacy segment、search continuation、`INVALID_CURSOR`、`CURSOR_STALE`。

## 5. Dialogs/account

覆盖 group/supergroup/channel/private/bot/Saved Messages/archive/forum/unread/pinned/muted/folder/migration safe metadata。Saved Messages 只能一个 `reference=me` row。`account get` 不输出 phone/credentials。

## 6. Chat details / participant roles

测试 owner/admin/member、admin title、bot/deleted account、权限不可枚举、current role semantics、unknown role 不强制 member、Basic Group 与 Channel/Supergroup API 路径。禁止显示名推断 owner/admin。

## 7. Structured sender / Rich MessageInfoV3

至少：user sender、channel/chat send-as、anonymous admin、reply/reply_top、forum_topic_id、forward origin、entities、views/forwards、reactions、poll、service action、media metadata、caption/text、MESSAGE_NOT_FOUND。

匿名管理员不得错误绑定具体 user。`availability` 不得伪造 deleted=true。

## 8. History / migration

`messages history`：newest→older、since inclusive、until exclusive、bounded memory、max500、不推进 read marker、不自动下载媒体。

Migration history 唯一键 `(source_chat_id,message_id)`，不能只按 message id 去重。legacy source 的 logical `chat_id` 仍是 current Supergroup，`source_chat_id` 指 legacy Basic Group。

## 9. Advanced search

测试 single/global、contains、sender-id、current sender-role、since/until、message type、topic、has-link、url-domain、cursor。

```text
mypikpak.com          match
cdn.mypikpak.com      match
mypikpak.com.evil.com reject
notmypikpak.com       reject
```

不访问 URL、不 follow redirect。Candidate scan 有上限，不为凑满结果无限读账号。

## 10. Forum

Telethon 1.44：`functions.messages.GetForumTopicsRequest(peer=...)`。测试 bounded topics pagination/cursor、TopicInfo、topic history rich schema、非 forum → `NOT_A_FORUM`。

## 11. Media metadata / explicit download

普通 history/search/get metadata-only，不能产生下载文件。

`media download` 测试：plan 第一次 `DOWNLOAD_CONFIRMATION_REQUIRED` 且不创建 output dir/不调用 download_media；token 绑定 chat/ids/output/allow-large+digest；token mismatch/过期拒绝；normal 20/500MiB、large hard 200/5GiB；filename/path safety；`.part`→atomic final；error/cancel 无半写最终文件；confirmed transport outcome 不自动 retry。

真实媒体下载不是默认 E2E，只有用户明确选择才产生本地文件。

## 12. JSON / JSONL / exit codes

JSON stdout 是单一 envelope，不混日志。JSONL = `meta → item* → end`，错误单行。

```text
2 INVALID_ARGUMENT
3 NOT_AUTHORIZED/AUTH_GUI_ONLY
4 CHAT_NOT_FOUND/MESSAGE_NOT_FOUND
5 AMBIGUOUS_CHAT
6 FLOOD_WAIT
7 WRITE_FAILED
8 SESSION_BUSY
9 EXPORT_IN_PROGRESS
10 WRITE_OUTCOME_UNKNOWN
11 DAEMON_UNAVAILABLE
12 INVALID_CURSOR/CURSOR_STALE
13 ACCESS_DENIED/MEMBERS_UNAVAILABLE
14 NOT_A_FORUM
15 DOWNLOAD_CONFIRMATION_REQUIRED
16 DOWNLOAD_LIMIT_EXCEEDED
130 Ctrl+C
```

Windows package test 必须检查 native Process ExitCode，不只看 PowerShell `$?`。

## 13. Security regression

普通日志不得包含：api_id/api_hash、phone/OTP/2FA、Session/credentials、IPC secret、access_hash/file_reference、message body/caption/URL text/media filename。

用户明确调用 history/search/get 时正文可在 stdout JSON/JSONL，但不能进入 app.log。写操作 body 不进 caplog。

## 14. FloodWait

Mock → `FLOOD_WAIT + retry_after_seconds`，不 retry storm。真人测试不故意制造 FloodWait。

## 15. v0.3 真人 E2E

默认不执行 send/forward/mark-read/media confirm download。用户本机验证：

1. dialogs 覆盖 group/supergroup/channel/private/bot/Saved/archive；
2. Chat Folder membership；
3. 真实聊天最近 500 history；
4. owner/admin；
5. sender-id/current role/domain filter；
6. anonymous admin/send-as 不误归属；
7. history/search 多页无重复/遗漏；
8. since/until；
9. Saved Messages history/search；
10. MESSAGE_NOT_FOUND；
11. AMBIGUOUS_CHAT；
12. v0.3 GUI + tgctl coexist；
13. legacy direct lock → packaged `SESSION_BUSY` + exit8；
14. GUI legacy-lock safe diagnostic，无 `database is locked`；
15. logs/stdout safety；
16. Forum 若账号有条件；
17. media metadata-only 不生成文件；
18. media plan 第一次不生成目录/文件；
19. **current-unread real scenario**：刷新 catalogue 后等待/制造时间差，再开始导出，确认该群开始时的新 unread 被包含；开始后才到的消息留到下一次。

Option-B real read-ack 或 media confirm 只有用户明确选择安全目标时才测。

## 16. Candidate / Release gate

记录 branch/runtime head、pytest 数量、Windows run、artifact、one-file/portable/tgctl SHA-256、CI 无法验证的真实 Telegram 项。

Candidate 完成后停止：**不 merge PR #20、不创建 v0.3.0 Release**，等待用户真人验收与明确发布授权。
