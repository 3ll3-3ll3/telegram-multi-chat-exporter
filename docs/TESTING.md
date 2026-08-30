# Testing Guide

本项目测试分四层。当前精确状态/冻结 Candidate 见 `HANDOFF.md`。

```text
1. unit/mock
2. Windows packaged CI
3. hash-traceable Candidate artifact
4. user real Telegram E2E
```

**CI green 不等于真实 Telegram E2E。**

## 1. Source test baseline

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
```

新行为必须尽量先有 deterministic unit/mock regression，再依赖真人 E2E。

## 2. Windows package CI

任何影响 Windows runtime 的 PR 至少检查：

- imports；
- PyInstaller build；
- packaged smoke；
- native process exit codes；
- artifact/hash generation。

v0.3 Candidate 当前 gate：

```text
pytest
GUI + daemon + reader + CLI import
TGExporter one-file build
TGExporter portable build
tgctl one-file build
standalone SESSION_BUSY JSON + native exit 8
portable SESSION_BUSY JSON + native exit 8
one-file GUI smoke
portable GUI smoke
standalone tgctl smoke
portable tgctl smoke
candidate SHA-256
artifact upload
```

不要只看 PowerShell `$?` 验证 CLI error code；使用 native Process ExitCode。

## 3. Stable GUI regression

不得破坏已经稳定/真人验证的：

- focused workspace；
- Telegram Chat Folder filter；
- avatar lazy load/failure fallback；
- Export Category create/persist/delete-without-disk-delete；
- `output/category/group/timestamp.json`；
- same-second no overwrite；
- Basic Group→Supergroup catalogue collapse；
- date-range current+legacy history；
- current-unread frozen boundary；
- Option B `JSON success → checkpoint → optional read ack`；
- since-last checkpoint；
- Windows system proxy；
- qasync non-blocking dialog/shutdown。

## 4. qasync regression

历史 bug：blocking modal/nested loop 可导致 asyncio task re-entry。

测试/审查要求：

- async paths 不使用 `QDialog.exec()` 或 static blocking dialog；
- shutdown cleanup 异常不会冒成 fatal top-level error；
- `disconnect()` awaitable/sync variants 都可处理；
- CLI Core 不依赖 Qt event loop。

## 5. v0.1.10 tgctl compatibility

必须长期保留：

- `status/chats list/messages search/messages get/forward/send`；
- JSON stdout 不混普通 log；
- `MESSAGE_NOT_FOUND` / `AMBIGUOUS_CHAT`；
- true forward；
- send plain text；
- dry-run；
- 20/200 forward cap；
- FloodWait structured stop；
- write body not logged；
- direct-session conflict safely `SESSION_BUSY`；
- packaged UTF-8 Chinese JSON；
- `SESSION_BUSY` native exit code 8。

v0.1.9 已真人验证实际 Saved Messages send/forward；不要为了每次回归向陌生目标执行 write。

## 6. v0.2/v0.3 daemon regression

- daemon unique Session owner；
- GUI/tgctl clients do not direct-open Session；
- authenticated Named Pipe JSON bytes；
- GUI + same-generation tgctl coexist；
- legacy direct Session holder → safe `SESSION_BUSY`；
- GUI close/crash does not cancel active daemon export；
- job metadata recoverable by reopened GUI；
- idle exit / on-demand wake；
- export active: Telegram reader waits；
- export active: real send/forward immediately `EXPORT_IN_PROGRESS`；
- write transport disconnect after submit → `WRITE_OUTCOME_UNKNOWN`, no replay。

## 7. Reader models / dialogs

Mock/API contract should cover:

```text
group
supergroup
channel
private
bot
Saved Messages
archive
forum
unread/pinned/muted
Telegram folder membership
migration metadata
```

Saved Messages must not duplicate the self dialog. Safe output must not expose access hashes/credentials.

## 8. Pagination / cursor

Must cover:

- default 100 / max 500；
- cursor HMAC sign/verify；
- method/query binding；
- tamper rejection；
- no `access_hash/file_reference/credential` in cursor；
- dialogs canonical stable pagination；
- history multi-page no overlap/gap；
- newest→older；
- Basic Group migration current→legacy segment transition；
- global/single search continuation；
- invalid → `INVALID_CURSOR`；
- unrecoverable continuation → `CURSOR_STALE`。

ADR: `docs/decisions/003-bounded-reader-pagination-and-safe-cursors.md`.

## 9. Migration regression

Critical cases:

- legacy row not duplicated in visible catalogue；
- do not merge unrelated same-name chats；
- current logical chat remains primary；
- history unique key `(source_chat_id,message_id)`；
- global search legacy cursor continues same segment without repeat/gap；
- rich get on legacy source returns current logical `chat_id` + legacy `source_chat_id`；
- current role snapshot for legacy messages uses current logical Supergroup entity。

These include bugs found in the 2026-08-30 pre-E2E tail audit and must remain regression-covered.

## 10. Members / sender identity

Test:

- owner/admin/member mapping；
- current-role semantics；
- unknown role not coerced to member；
- admin title；
- bot/deleted account safe representation；
- permissions unavailable；
- Basic Group vs Supergroup/Channel APIs；
- channel/chat send-as；
- anonymous admin without hidden-user inference。

Never infer role/identity from display name or `post_author`.

## 11. Rich MessageInfoV3

At least:

```text
chat_id / source_chat_id / message_id
date/edit_date
structured sender
text/caption
entities
reply/reply_top
forum_topic_id
forward origin
grouped_id
views/forwards
reactions
poll
service action
pinned
media metadata
availability
```

Missing message remains `MESSAGE_NOT_FOUND/not_found_or_unavailable`, not fabricated deleted=true.

## 12. Advanced search

Cover single/global:

- contains；
- sender ID；
- current sender role；
- since/until；
- message type；
- Forum topic；
- has-link；
- URL domain；
- cursor/limit。

URL domain security examples:

```text
example.com              match
cdn.example.com          match
example.com.evil.test    reject
notexample.com           reject
```

Do not access target URLs or follow redirects. Candidate scan stays bounded and continues via cursor.

## 13. Forum

Test topic list/history, bounded pagination/cursor, rich topic-history schema and non-forum → `NOT_A_FORUM`.

Live Forum E2E is conditional on the user's account having a suitable forum.

## 14. Media metadata / explicit download

Normal history/search/get is metadata-only and must not create files.

Download tests:

- first call → `DOWNLOAD_CONFIRMATION_REQUIRED`；
- plan does not create output dir or call download；
- token binds chat/ids/output/large flag/plan digest；
- mismatch/expiry rejected；
- normal 20 files/500 MiB；
- explicit large hard cap 200 files/5 GiB；
- unknown-size actual bytes still enforce cap；
- safe basename/path traversal handling；
- `.part` → atomic final rename；
- error/cancel does not leave partial file pretending success；
- confirmed transport outcome is not auto-retried。

Real media download is **not** default human E2E; only when user explicitly chooses.

## 15. Security regression

Ordinary logs/cursors/safe JSON must not leak:

```text
api_id/api_hash
phone/OTP/2FA
Session/credentials
IPC secret
access_hash/file_reference
message body/caption/URL text/media filename
```

Message body is allowed only as explicit reader stdout data.

Test safe exception mapping; avoid raw TL object repr in logs.

## 16. Exit codes

Important CLI codes:

```text
2  INVALID_ARGUMENT
3  NOT_AUTHORIZED / AUTH_GUI_ONLY
4  CHAT_NOT_FOUND / MESSAGE_NOT_FOUND
5  AMBIGUOUS_CHAT
6  FLOOD_WAIT
7  WRITE_FAILED
8  SESSION_BUSY
9  EXPORT_IN_PROGRESS
10 WRITE_OUTCOME_UNKNOWN
11 DAEMON_UNAVAILABLE
12 INVALID_CURSOR / CURSOR_STALE
13 ACCESS_DENIED / MEMBERS_UNAVAILABLE
14 NOT_A_FORUM
15 DOWNLOAD_CONFIRMATION_REQUIRED
16 DOWNLOAD_LIMIT_EXCEEDED
130 Ctrl+C
```

## 17. Human Telegram E2E for v0.3

Before merge/release, user machine should validate the frozen Candidate listed in `HANDOFF.md`.

Read-first checklist:

1. dialogs: group/supergroup/channel/private/bot/Saved/archive；
2. Telegram Folder membership；
3. real 500-message history；
4. owner/admin；
5. sender/current role/domain filters；
6. anonymous admin/send-as not misattributed；
7. history/search multiple pages no overlap/gap；
8. since/until；
9. Saved Messages history/search；
10. `MESSAGE_NOT_FOUND`；
11. `AMBIGUOUS_CHAT`；
12. v0.3 GUI + tgctl coexist；
13. legacy direct lock → packaged `SESSION_BUSY` + exit 8；
14. GUI under legacy lock gives safe diagnostic, no raw `database is locked`；
15. log/stdout safety；
16. Forum if available；
17. metadata-only creates no media files；
18. media plan creates no directory/files。

Do not intentionally trigger FloodWait. Default E2E does not send/forward/mark-read. Real media confirm download only with explicit user choice.

## 18. v0.3 release gate

Current rule:

```text
automated Candidate green
→ frozen hash-traceable runtime
→ human E2E PASS
→ explicit user release authorization
→ merge/release
```

If E2E discovers runtime issues: fix only actual issue, add regression, rerun Windows CI, revalidate affected live scenario.

ADR: `docs/decisions/006-human-e2e-release-gate.md`.

## 19. Documentation-only handoff PR

The AI handoff docs PR should still run normal PR CI because `pull_request` triggers Windows build. A docs-only change does not need a new formal Release, but CI must be green before considering the documentation safe to merge.