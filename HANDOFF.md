# HANDOFF.md

> 当前开发交接快照。任何 Agent 接手前先读 `AGENTS.md`，再读本文件；在核对 GitHub 当前事实前不要修改代码。

更新时间：2026-08-30

# Current Project State

- Repository: `3ll3-3ll3/tg-exporter`
- Production version: **v0.3.0**
- Production commit/tag: `8e230e33ea928bcf71296e4e5379b097446dbec5` / `v0.3.0`
- Current development version: **v0.3.1 runtime-fix candidate line**
- Development branch: `codex/v0.3.1-runtime-fixes`
- Base: `main@8e230e33ea928bcf71296e4e5379b097446dbec5`
- v0.3.0 tag/Release: immutable; do not move, overwrite, delete, or rebuild in place
- Current task: finish v0.3.1 validation and PR; **do not publish a v0.3.1 Release without explicit user authorization after human acceptance**

## Why v0.3.1 exists

Real v0.3.0 acceptance found three runtime-quality problems to address:

1. packaged `tgctl messages search --url-domain ...` could crash in domain normalization;
2. normal Alt+F4 GUI close could log `Fatal application error` / `RuntimeError: Event loop stopped before Future completed`;
3. real bounded message samples contained too many `sender_type=unknown`, and `owner_visibility=not_found` was too coarse.

The patch must preserve all v0.3.0 security and single-daemon invariants.

# Architecture / safety invariants

```text
TGExporter GUI ─┐
               ├─ authenticated Windows Named Pipe → TG daemon → Telethon → one user Session
tgctl / Codex ─┘
```

- daemon remains the only normal Telegram Session owner;
- GUI close only detaches its lease and local tasks; it must not terminate the shared daemon;
- reader remains bounded/default 100/max 500 and does not download media by default;
- real send/forward remain explicit write operations with dry-run support and existing caps;
- current-unread export keeps the v0.3.0 per-group export-start snapshot semantics;
- no secret, Session content, phone/OTP/2FA, access hash/file reference, message body, caption, URL, or media filename may enter ordinary logs/Issues/PRs/CI artifacts;
- no real send/forward, mark-read, media download, group mutation, FloodWait stress, or Session reset during default acceptance.

# v0.3.1 fixes

## 1. Packaged url-domain crash

Root cause: v0.3.0 domain normalization relied on Python runtime codec lookup for `"idna"`. Source Python had the codec, while frozen PyInstaller execution could miss the dynamically resolved codec/module and fail before filtering.

Fix:

- explicit offline standard-library IDNA normalization;
- explicit domain/URL validation and canonical host extraction;
- malformed input → `INVALID_ARGUMENT`, never a generic `TELEGRAM_ERROR`;
- no public-suffix download/network dependency;
- PyInstaller tgctl build includes `encodings.idna` as defense in depth;
- CI directly executes url-domain smoke on final standalone and portable `tgctl.exe`.

Regression coverage includes bare domain, `www`, case, full URL, subdomain, whitespace, invalid input, no match, suffix lookalikes, pagination, and cursor query binding.

## 2. GUI normal-close fatal

Root cause: v0.3.0 waited for Qt `aboutToQuit` and then attempted async shutdown, but Qt/qasync could already have stopped the underlying event loop. `run_until_complete` then observed unfinished work and raised `Event loop stopped before Future completed`.

Fix order:

```text
last window closes
→ keep Qt event loop alive
→ cancel/await GUI init + job-monitor tasks
→ cancel/await proxy heartbeat
→ client.detach GUI lease
→ async app coroutine returns
→ Qt/qasync event loop ends normally
```

No `loop.stop()` is used to interrupt unfinished shutdown. Real shutdown exceptions remain logged/re-raised.

## 3. Sender / owner diagnostics

Sender identity now uses Telegram-provided fields only: `sender`, `from_id`, `peer_id`, `sender_id`, `sender_chat`, `post_author`, `via_bot_id`; it never guesses from text, links, or nicknames.

Recoverable cases include user, channel/chat send-as, broadcast channel posts, anonymous admins, and deleted-user entities when Telegram still supplies a peer. `forward_origin` is always separate from the actual sender.

If Telegram does not provide enough identity information, keep `sender_type=unknown` and set a reason such as:

- `service_message_without_sender`
- `forwarded_message_without_actual_sender`
- `post_author_without_sender_peer`
- `unsupported_or_unavailable_sender_peer`
- `telegram_sender_not_provided`

Owner visibility distinguishes at least: `available`, `insufficient_permissions`, `participants_unavailable`, `creator_not_in_returned_page`, `telegram_not_returned`, and supportable `not_found` cases.

All new fixtures are synthetic/de-identified.

# Automated validation

First fully green runtime candidate before documentation-only handoff commits:

```text
runtime head: 9496416e081178d87e2fed3ccda0c248c3c18c40
Windows run: 33302689526
result: success
pytest: 125 passed in 1.94s
focused v0.3.1 tests: 30 passed in 0.52s
compileall: success
git diff --check: success
source url-domain smoke: success
one-file GUI build: success
portable GUI build: success
tgctl build: success
packaged standalone url-domain smoke: success
packaged portable url-domain smoke: success
packaged SESSION_BUSY JSON/native exit=8: success
packaged GUI/tgctl smoke: success
repository worktree clean gate: success
```

Candidate artifact from that runtime head:

```text
artifact id: 9729505508
artifact name: TGExporter-v0.3.1-candidate-windows-x64
outer artifact ZIP SHA-256:
43cfd77feb2c2aff2b05b8a8dd057d1d3605a1f24b75430431ddd3798800f32c

TGExporter-v0.3.1-windows-x64.exe
389f970e60a0d473df2a2f46a1c9a6d503a14235bb024c5b3d823323a68e6b15

TGExporter-v0.3.1-windows-x64-portable.zip
5613210ea2b7b29a651c1fa6f84fe7eabaf7abbbf0d46f71de00e67a48642b2d

tgctl.exe
171056684c793f71619596ef60de1c6f8192d99f956f6e248945cf5c762196f5
```

These hashes belong specifically to run `33302689526` / runtime head `9496416e...`. Documentation commits after that head require final PR-head CI before merge; do not silently relabel these hashes as belonging to a later build.

# Remaining acceptance gate

Automated CI cannot replace the real-account/local-Windows checks. Before calling v0.3.1 release-ready, still verify on the user's authorized machine/account, without forbidden writes:

1. packaged `tgctl.exe` real-chat domain search;
2. idle GUI close;
3. refresh-groups then close;
4. a 0-message current-unread export with mark-read disabled, then close;
5. two GUI instances started together and closed one by one;
6. `tgctl status` after each close remains usable and no GUI close ends the shared daemon;
7. new log segment contains zero normal-close Fatal/Traceback/un-awaited-coroutine/Task-destroyed entries;
8. re-run the same bounded sender sample used for the v0.3.0 finding and report before/after counts without committing or displaying real message bodies/URLs/IDs;
9. privacy audit reports counts only, not sensitive log lines.

If a requested check would require real send/forward, mark-read, media download, group mutation, FloodWait stress, or Session reset, stop and obtain separate user authorization.

# Current workflow

1. finish documentation on `codex/v0.3.1-runtime-fixes`;
2. require the final branch head Windows CI to PASS;
3. create/open PR from `codex/v0.3.1-runtime-fixes` to `main`;
4. keep PR unmerged until the remaining human acceptance is recorded;
5. after human PASS and explicit user authorization, merge through PR;
6. only then prepare a **new** `v0.3.1` tag/Release; never alter `v0.3.0`.

# New Chat Resume Instructions

A new agent should read:

1. `AGENTS.md`
2. this `HANDOFF.md`
3. `README.md`
4. `docs/CODEX_TGCTL.md`
5. `docs/releases/v0.3.0.md`
6. `docs/releases/v0.3.1.md`
7. architecture/security/testing/release docs as needed

Then verify GitHub current `main`, `v0.3.0` Release/tag, `codex/v0.3.1-runtime-fixes`, its PR, and latest Windows CI. GitHub current facts override this snapshot.
