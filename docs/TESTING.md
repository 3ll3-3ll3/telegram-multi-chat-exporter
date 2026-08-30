# Testing Guide — v0.3 Candidate

本项目测试分四层：

1. unit/mock：模型、cursor、reader/filter、daemon scheduling、GUI legacy 行为、安全边界；
2. Windows package CI：TGExporter/tgctl PyInstaller、真实 OS Session lock、native exit code；
3. candidate artifact：可下载 EXE + SHA-256；
4. 用户真实 Telegram 只读 E2E。

**CI green 不等于真实账号 E2E。**

## 1. CI 基线

```powershell
pip install -e ".[dev]"
pytest -q
```

v0.3 最新 head 必须继续通过：

```text
pytest -q
GUI + reader/tgctl import
TGExporter one-file PyInstaller
tgctl one-file PyInstaller
legacy OS Session lock -> packaged SESSION_BUSY JSON + native exit 8
TGExporter packaged smoke
tgctl packaged smoke
artifact upload
```

## 2. GUI/v0.2 regression

不得因 Reader 破坏：focused workspace、Telegram Chat Folder、avatar lazy load、Export Category、category/group/timestamp JSON、same-second no overwrite、migration collapse/date-range history、frozen current unread、Option B 顺序、since-last checkpoint、qasync shutdown。

v0.3 GUI 与 v0.3 tgctl 都经 daemon，正常同时存在不应 `SESSION_BUSY`。export 活跃时 reader 等待；真实 send/forward 立即 `EXPORT_IN_PROGRESS`。

## 3. Cursor / page

必须覆盖：

- default 100 / max 500；
- cursor HMAC sign/verify；
- method/query mismatch；
- tamper；
- cursor 不含 access_hash/file_reference/credential；
- dialogs canonical pagination 不重复；
- history 2+ pages no overlap/gap；
- migration current→legacy segment transition；
- search continuation；
- invalid → `INVALID_CURSOR`；stale entity → `CURSOR_STALE`。

## 4. Dialogs/account

Mock/API contract 覆盖：group/supergroup/channel/private/bot/Saved Messages/archive/forum/unread/pinned/muted/folder/migration。Saved Messages 只能出现一个 `reference=me` row。

`account get` 只允许 safe account fields，不允许 phone/credentials。

## 5. Chat details / participant roles

测试：owner/admin/member mapping、admin title、bot/deleted account、权限不可枚举、current role semantics、unknown role 不强制 member、Basic Group 与 Channel/Supergroup API 路径。

禁止显示名推断 owner/admin。

## 6. Structured sender / rich messages

至少测试：

```text
user sender
channel/chat send-as
anonymous admin
reply / reply_top
forum_topic_id
forward origin
entities
views / forwards
reactions
poll
service action
media metadata
caption vs text
MESSAGE_NOT_FOUND
```

匿名管理员不得错误绑定具体 user。`availability` 不得伪造 deleted=true。

## 7. History

`messages history`：newest→older、since inclusive、until exclusive、bounded memory、max 500、不推进 read marker、不下载媒体。

Migration history 唯一键 `(source_chat_id,message_id)`，不能只用 message id 去重。

## 8. Advanced search

测试：single/global、contains、sender-id、current sender-role、since/until、message type、topic、has-link、url-domain、cursor。

关键安全测试：

```text
mypikpak.com                 match
cdn.mypikpak.com             match
mypikpak.com.evil.com        reject
notmypikpak.com              reject
```

不访问 URL、不 follow redirect。Candidate scan 有上限，不为凑满结果无限读取。

对已取到内存的 500 条纯文本候选，本地过滤目标 <1s；Telegram network time 单独计。

## 9. Forum

Telethon 1.44 契约使用：

```text
functions.messages.GetForumTopicsRequest(peer=...)
```

不是 channels namespace。

测试 topics bounded pagination/cursor、TopicInfo 字段、topic history rich schema、非 forum → `NOT_A_FORUM`。

## 10. Media metadata / explicit download

普通 history/search/get 只测试 metadata，不能产生下载文件。

`media download` 测试：

- plan 第一次 `DOWNLOAD_CONFIRMATION_REQUIRED`；
- plan 不创建 output dir、不调用 `download_media`；
- token 绑定 chat/ids/output/allow-large + plan digest；
- token query mismatch/过期拒绝；
- normal 20 files / 500 MiB；
- large hard 200 files / 5 GiB；
- >hard cap 在下载前拒绝；
- filename/path traversal safety；
- `.part` -> atomic final rename；
- error/cancel 不留下半写最终文件；
- confirmed transport outcome 不自动 retry。

真实账号媒体下载不是默认 E2E；只有用户明确选择测试时才产生本地文件。

## 11. JSON / JSONL

JSON：一份 envelope，stdout 不混 log。

JSONL：

```text
meta
item * N
end(count,next_cursor,has_more,timing,...)
```

错误为单行 error。Reader page 仍 bounded，不把 Named Pipe 变成无界 stream。

## 12. Exit codes

保留历史并新增：

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

Windows package test 必须用 native Process ExitCode，而不是仅看 PowerShell `$?`。

## 13. Security regression

必须验证普通日志不含：

```text
api_id / api_hash
phone / OTP / 2FA
Session / credentials
IPC secret
access_hash / file_reference
message body / caption / URL text / media filename
```

Rich safe serializer/cursor 不得出现 `access_hash/file_reference`。写操作仍测 body 不进 caplog。

## 14. FloodWait

Mock → `FLOOD_WAIT + retry_after_seconds`，不自动循环 retry。真人测试不故意制造 FloodWait。

## 15. v0.3 真人只读 E2E

默认不执行 send/forward/mark-read/media download。Desktop Codex/用户本机验证：

1. dialogs 覆盖 group/supergroup/channel/private/bot/Saved/archive；
2. Chat Folder membership；
3. Svip 最近 500 history；
4. owner/admin；
5. 最近 500 条谁发 pikpak；
6. 谁发真实 mypikpak.com；是否当前 owner/admin；
7. structured sender；
8. anonymous admin/send-as 不误归属；
9. history 多页无重复/遗漏；
10. since/until；
11. Saved Messages history/search；
12. MESSAGE_NOT_FOUND；
13. AMBIGUOUS_CHAT；
14. v0.3 GUI + tgctl coexist，不应 busy；
15. legacy direct lock → packaged `SESSION_BUSY` + exit 8；
16. legacy lock 下 GUI safe diagnostic，无 `database is locked`；
17. FloodWait 仅自然出现时验证；
18. logs/stdout safety；
19. Forum 若账号有条件；
20. media metadata-only 不生成文件；
21. media plan 第一次不生成文件。

## 16. Candidate gate

完成后记录：branch/head、pytest 数量、Windows run id、artifact、两个 EXE SHA-256、无法由 CI 验证的真实 Telegram 项目。

然后**停止**：不 merge Release commit、不创建 `v0.3.0` Release，等用户本地验收与明确发布授权。
