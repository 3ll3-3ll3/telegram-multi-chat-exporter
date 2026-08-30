# HANDOFF.md

> 当前项目交接快照。新 Agent / GPT 接手时先读 `AGENTS.md`，再读本文件；恢复检查完成前不要修改代码。

# Current Project State

**Last updated:** 2026-08-30 14:00 +08:00  
**Repository:** `3ll3-3ll3/tg-exporter`  
**Default branch:** `main`  
**Production version:** `v0.1.10`  
**Production commit/tag:** `cedb02035597aa607fac399666154519f480c431` / `v0.1.10`  
**Current development version:** `v0.3.0` Candidate  
**Current development branch:** `codex/personal-account-reader-v0.3.0`  
**Current development branch tip at audit:** `7282326e3ce51a294b90840e9cf7c965ad304fc7`  
**Frozen pre-KI-001 runtime candidate:** `0ad4219ef367d28326b5aca705fffe1d007db52b`  
**Current task:** fix KI-001 current-unread snapshot timing → new Candidate → real Telegram E2E  
**Related Issue:** #22 `fix: snapshot current unread at each group's export start`  
**Related PR:** Draft PR #20 `feat: v0.3.0 personal account reader candidate`  
**Handoff docs PR:** #21 `docs: persist project context for AI handoff`  
**Release gate:** no PR #20 merge / no v0.3.0 Release until #22 fixed + human E2E PASS + explicit user release authorization

## Source-of-truth warning

`main` is the formal Production line, not the newest runtime. v0.3 daemon/reader implementation is in PR #20.

Historical Draft PRs #17 (daemon design) and #19 (reader design) are design references already absorbed by #20; they are not current implementation entry points. Old branch `docs/agent-handoff` is also historical.

# Project Summary

TG Exporter / TG 导出器 is a Windows-local Telegram tool:

- GUI: export multiple selected chats independently to text/caption JSON;
- `tgctl`: Codex/CLI machine interface for reads/search plus bounded true-forward/plain-text send;
- v0.2/v0.3: one local daemon owns Telegram Session, GUI/tgctl use local IPC;
- v0.3 Personal Account Reader: paged account/dialog/member/rich-message/Forum/Saved Messages/media-metadata access plus explicit two-stage local media download.

It is not Telegram Desktop replacement, cumulative archive DB, cloud service, Bot API app, or 24/7 autonomous agent.

# Production Definition

There is no remote production DB/server/cloud runtime. Production means:

1. formal GitHub Release Windows binaries;
2. user-local `%APPDATA%\TelegramMultiChatExporter\` Session/config/state/log/cache;
3. the user's real Telegram account;
4. user-selected export folders.

# Production Version

Latest formal Release: **v0.1.10**, target `cedb02035597aa607fac399666154519f480c431`.

`https://github.com/3ll3-3ll3/tg-exporter/releases/tag/v0.1.10`

```text
TGExporter-v0.1.10-windows-x64.exe
sha256 b598aecdd7fcc3f5731ba955f7f02d8bd45ea47220f66a040bc20b64f4e410be

TGExporter-v0.1.10-windows-x64-portable.zip
sha256 113c6f8223d6f648571bf8ad3e86a1df1db2ad1e118bb2674e70f0031b0274dd

tgctl.exe
sha256 ebd6cd8898f51aa9e63a7efa6292a70df0afe15cd5efe99b7fc4be9bbf2f5efa
```

v0.1.10 fixes packaged Windows non-UTF-8 Chinese JSON error handling so `SESSION_BUSY` retains native exit code 8. The fix/regressions were forward-ported to v0.3 Candidate.

# Current Architecture

## Production v0.1.10

```text
GUI ─┐
     ├→ direct TelegramService/Telethon → one SQLiteSession
 tgctl┘
```

OS `SessionLease` prevents concurrent direct ownership. Never bypass/copy the Session.

## Candidate v0.3

```text
GUI ─┐
     ├→ authenticated Windows Named Pipe + UTF-8 JSON → TG daemon → TelegramService/Telethon → one Session
 tgctl┘
```

Daemon is the only Session owner. Same-generation GUI + tgctl coexist; `SESSION_BUSY` is only a compatibility boundary when an old direct process already owns the Session.

```text
LOCAL status/job/heartbeat       → immediate
export                           → exclusive Telegram job
reader                           → waits during export
real send/forward during export  → EXPORT_IN_PROGRESS, never queued
```

See `docs/ARCHITECTURE.md`, `docs/SECURITY_MODEL.md`, ADRs, and PR #20 design docs.

# Core Product Invariants

- output: `root / Export Category / group / YYYY-MM-DD_HH-mm-ss.json`; same-second `_2/_3/...`;
- Export Category is local software state, not Telegram Chat Folder; deleting a category does not delete old files;
- each JSON independent; do not read/merge/overwrite historical exports;
- GUI message export is text/caption only; group avatar is UI-cache exception;
- Basic Group→Supergroup shows one current logical group; legacy peer is historical source only;
- current-unread requires a deterministic frozen snapshot; **accepted timing is each group's export start (ADR-007), not catalogue refresh**;
- mark-read default OFF; `JSON atomic success → checkpoint → optional read ack`;
- async Qt/Telethon uses qasync non-blocking dialogs; do not reintroduce nested modal exec;
- compatibility AppData path remains `%APPDATA%\TelegramMultiChatExporter\`.

# Completed

## Stable v0.1.x

Windows GUI export, focused workspace, Telegram Folder filter, avatar lazy loading, local Export Categories, Basic Group→Supergroup catalogue/history handling, current-unread/since-last/Option-B ack, Windows system proxy, qasync fixes, tgctl status/chats/search/get/forward/send, JSON/error contract, dry-run/20-200 caps/ambiguity/FloodWait, v0.1.9 real Saved Messages send/forward E2E, v0.1.10 packaged UTF-8/exit-code hotfix.

## v0.2 inherited by v0.3

`codex/single-daemon-v0.2.0 @ 165b0a86c85049cb25ab51f601c210ef986556a2`: single daemon, Named Pipe IPC, GUI/tgctl clients, tray, lease/heartbeat, daemon-side export, coordinator, idle shutdown, write scheduling. It was not separately formally released; v0.3 inherits it.

## v0.3 Candidate主体

PR #20 implements:

```text
tgctl account get
tgctl dialogs list
tgctl chats get/chats members
tgctl messages history/search/get
tgctl topics list/history
tgctl media download
```

Reader has default page 100/max500, HMAC/query-bound cursors, Rich MessageInfoV3, current role snapshots, anonymous/send-as safety, current→legacy migration history, hostname domain filter, Forum, metadata-only media and explicit confirmed downloads.

## Pre-E2E tail fixes already completed

- standalone+portable packaged `SESSION_BUSY JSON/native exit=8` release gate restored;
- release import gate includes daemon+reader+tgctl;
- cp1252/UTF-8 source regression preserved;
- migrated global search legacy cursor duplicate/gap bug fixed;
- single-chat migrated cursor segment/stale semantics added;
- migrated role snapshot uses current logical Supergroup;
- legacy rich-get logical/source IDs aligned;
- one-file+portable Candidate CI;
- `main@v0.1.10` integrated into #20 ancestry and #20 retargeted to main;
- no unresolved #20 review thread at audit time.

# Frozen Pre-KI-001 Candidate

Traceability only; do **not** treat this as final release candidate until Issue #22 is fixed:

```text
runtime: 0ad4219ef367d28326b5aca705fffe1d007db52b
Windows run: 33293667296 = success
pytest: 91 passed
artifact: 9726786295
https://github.com/3ll3-3ll3/tg-exporter/actions/runs/33293667296/artifacts/9726786295
```

```text
one-file EXE  94f43dadc421e67de0a5f8cb7d1ff0b3f98bb85e46a46ca423c9d7d025fc55c6
portable ZIP  6d0dad9514eab1ff1c4d80b35df704951fc7fe63ff23bea2536dcf01c19626bc
tgctl.exe     aee8edbe9c7693b3fa299757bc386b285c42003e03d787718903b7223ae638a0
outer artifact 37309a137577f8aa3de63bc5ff2a188147b1908be5d4e7a0e53df531358503f7
```

The later `7282326e...` branch tip was docs-only and also had green Windows run `33294055220`.

# In Progress

Issue #22 / KI-001 is now the first task. After it is fixed and a new Candidate is frozen, perform the real-account E2E. Do not add unrelated features, merge #20, or release v0.3 meanwhile.

# Pending

After #22 fix, human E2E covers:

- all dialog types + Telegram Folder;
- real 500 history;
- owner/admin and sender/current-role/domain filters;
- anonymous/send-as identity safety;
- multi-page history/search no overlap/gap;
- since/until;
- Saved Messages;
- MESSAGE_NOT_FOUND / AMBIGUOUS_CHAT;
- v0.3 GUI + tgctl coexist;
- legacy direct lock → SESSION_BUSY + native exit 8;
- GUI safe legacy-lock diagnostic;
- log/stdout safety;
- Forum if available;
- metadata-only no files;
- media plan no directory/files;
- real media confirm only if user explicitly chooses.

Do not intentionally trigger FloodWait. Default v0.3 E2E does not need to repeat send/forward/mark-read.

# Known Bugs

## Issue #22 / KI-001 — Current-unread snapshot timing mismatch (OPEN)

Full details: `docs/KNOWN_ISSUES.md`, ADR-007, <https://github.com/3ll3-3ll3/tg-exporter/issues/22>.

Accepted semantics: each group freezes `read_inbox_max_id/latest_message_id` **when that group's export begins**, then exports only `lower < id <= upper`; optional acknowledgement uses that exact upper bound after JSON+checkpoint.

Current runtime instead uses `GroupInfo` captured at catalogue load/refresh. `exporter.py` explicitly documents catalogue-refresh freezing; daemon `ExportCoordinator` passes the serialized plan without a per-group read-state refresh. This is a correctness mismatch and release blocker unless user changes the requirement.

Historical fixed regression knowledge: qasync nested modal task re-entry; packaged cp1252 Unicode error/exit1; migrated global-search legacy cursor repeat/gap; migrated rich-get ID mismatch.

# Known Risks

- GitHub branch protection is absent; no-direct-main/no-force/release discipline is self-enforced;
- v0.3 lacks systematic real-account E2E;
- Telegram cannot prove historical admin tenure, hidden anonymous identity or deleted status; return unknown/unavailable rather than guess;
- media download is a local-disk side effect;
- legacy direct binaries can intentionally hit SessionLease compatibility boundary;
- open historical Draft PR #17/#19 can confuse agents;
- frozen pre-#22 hashes must be replaced after runtime fix.

# Technical Debt

- v0.2 implemented but not separately released; v0.3 inherits it;
- detailed v0.3 design remains in PR #20 branch until merge;
- historical monolithic DECISIONS now coexists with ADR index;
- MCP remains future direction only;
- runtime/docs/tests still need alignment to ADR-007 after #22.

# Important Constraints

Keep AppData path; do not delete historical JSON; do not copy/bypass Session lock; do not infer migration by name; do not infer anonymous identity from text; do not call unavailable messages deleted; reader never implicitly writes/marks read; Actions Artifact is not Production; AV/code-signing work is deprioritized.

# Production Safety Boundaries

No Secrets/Session contents in repo/log/CI; no AppData deletion/migration shortcut; no direct/force push main; no tag/Release overwrite/delete; real Telegram writes require explicit authorization; real media download requires explicit choice; no daemon TCP/HTTP/Web exposure; no real Telegram credentials in Actions.

See `docs/SECURITY_MODEL.md` and `SECURITY.md`.

# Recent Decisions

ADR-001 single daemon; ADR-002 local authenticated Named Pipe; ADR-003 bounded safe cursors; ADR-004 explicit bounded writes/no automatic replay; ADR-005 migrated logical identity; ADR-006 human E2E release gate; ADR-007 per-group export-start unread snapshot.

# Next Steps

1. Work on Issue #22 in PR #20 branch only;
2. fetch safe current read/latest state immediately before each unread group's export;
3. add regression for stale catalogue/new export-start snapshot, post-snapshot arrival exclusion, exact ack bound and per-group multi-batch snapshot;
4. rerun full v0.3 Windows Candidate gate;
5. freeze new runtime/artifact/hashes and update PR/HANDOFF;
6. run real Telegram E2E;
7. fix only actual E2E failures and revalidate affected paths;
8. after all PASS, wait for explicit user `v0.3.0` release authorization;
9. finalize release notes → merge/release → verify tag/target/assets/SHA256/workflow → update Production state.

# Recommended Next Task

**Fix Issue #22 / KI-001. This is a correctness fix, not new scope.** Do it before asking the user to spend time on full v0.3 real-account E2E.

# How To Resume

1. Check main + Latest Release;
2. check Issue #22;
3. check PR #20 OPEN/DRAFT/base/head/CI;
4. read `docs/KNOWN_ISSUES.md` + ADR-007;
5. inspect PR #20 `exporter.py`, `read_state.py`, `export_coordinator.py`;
6. read PR #20 daemon/reader designs and relevant ADRs;
7. do not modify unrelated code;
8. if a newer commit already fixed #22, verify regression/CI/new frozen artifact and update HANDOFF before E2E.

# New Chat Resume Instructions

Before editing code, a new GPT must read:

1. `AGENTS.md`;
2. `HANDOFF.md`;
3. `README.md`;
4. `docs/KNOWN_ISSUES.md`;
5. `docs/ARCHITECTURE.md`;
6. `docs/SECURITY_MODEL.md` + `SECURITY.md`;
7. `docs/TESTING.md`, `docs/DEPLOYMENT.md`, `docs/RELEASE_PROCESS.md`;
8. relevant `docs/decisions/` ADRs;
9. Issue #22, PR #20, and historical PR #17/#19;
10. main/dev branch commits, CI, Latest Release/Tags.

Before changes, report to the user: current project state, current task, current known bug/risk, and recommended next action. If GitHub facts differ, GitHub wins; update HANDOFF first.