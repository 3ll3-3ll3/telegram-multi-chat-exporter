# HANDOFF.md

> 当前开发交接快照。任何 Agent 接手前先读 `AGENTS.md`，再读本文件；GitHub 当前事实若与文档冲突，以 GitHub 为准。

更新时间：2026-08-30

# Current Project State

- Repository: `3ll3-3ll3/tg-exporter`
- Production: **v0.3.0**
- Production commit/tag: `8e230e33ea928bcf71296e4e5379b097446dbec5` / `v0.3.0`
- Development: **v0.3.1 runtime-fix candidate**
- Branch: `codex/v0.3.1-runtime-fixes`
- Base: `main@8e230e33ea928bcf71296e4e5379b097446dbec5`
- PR: **#24**, intentionally Draft until local Windows / real-account acceptance passes
- Formal `v0.3.0` tag/Release must never be moved, overwritten, deleted, or rebuilt in place
- Do not merge or publish `v0.3.1` without final human acceptance and explicit user authorization

## Why v0.3.1 exists

v0.3.0 acceptance exposed runtime-quality issues and one missing required search capability:

1. packaged `tgctl messages search --url-domain ...` could crash in domain normalization;
2. normal GUI close could hit `RuntimeError: Event loop stopped before Future completed`;
3. sender/owner diagnostics were too coarse for real bounded samples;
4. the required acceptance matrix included `regex`, but v0.3.0 did not actually expose a regex parameter.

v0.3.1 fixes those issues without expanding Telegram write permissions or weakening the single-daemon model.

# Architecture / safety invariants

```text
TGExporter GUI ─┐
               ├─ authenticated Windows Named Pipe → TG daemon → Telethon → one user Session
tgctl / Codex ─┘
```

- daemon remains the only normal Telegram Session owner;
- GUI close detaches only its own lease/tasks and must not shut down the shared daemon;
- reader remains bounded: default page 100, max 500; global candidate scan remains capped;
- ordinary history/search/get remain media-metadata-only;
- real send/forward remain explicit operations with existing dry-run/cap/error semantics;
- current-unread keeps the v0.3.0 per-group export-start frozen snapshot invariant;
- no API hash, phone/OTP/2FA, Session content, IPC secret, access hash/file reference, message body/caption/URL/media filename may enter ordinary logs/Issues/PRs;
- default acceptance must not perform real send/forward, mark-read, confirmed media download, group mutation, FloodWait stress, or Session reset.

# v0.3.1 fixes

## Packaged url-domain

- explicit offline stdlib IDNA normalization;
- strict host/URL validation and canonical hostname extraction;
- malformed input → `INVALID_ARGUMENT`, not generic `TELEGRAM_ERROR`;
- no PSL/network dependency;
- PyInstaller tgctl build includes `encodings.idna` as defense in depth;
- final standalone and portable `tgctl.exe` run the same packaged search-filter smoke.

## GUI normal close

Shutdown ordering is now:

```text
last window closes
→ keep Qt event loop alive
→ cancel/await GUI init + job-monitor tasks
→ cancel/await proxy heartbeat
→ client.detach GUI lease
→ async app coroutine returns
→ Qt/qasync loop ends normally
```

No `loop.stop()` is used to hide unfinished shutdown; genuine failures remain logged.

## Sender / owner diagnostics

Sender identity uses Telegram-provided fields only (`sender`, `from_id`, `peer_id`, `sender_id`, `sender_chat`, `post_author`, `via_bot_id`). It never guesses identity from message text, links, titles, or nicknames. `forward_origin` stays separate from the actual sender.

When Telegram does not provide enough identity information, `sender_type=unknown` remains and `unknown_reason` explains the class, e.g. service-without-sender, forward-without-actual-sender, post-author-without-peer, unsupported/unavailable peer, or Telegram sender not provided.

Owner visibility now distinguishes availability, insufficient permissions, participants unavailable, bounded page not containing creator, Telegram not returning creator, and supportable not-found cases.

## Bounded regex search

```powershell
tgctl messages search --chat <ref> --regex "release-\d+" --json
```

- local Python regex inside the existing bounded candidate scan;
- default case-insensitive; `--case-sensitive` switches behavior;
- composes with contains/domain/sender/sender-role/time/type/topic filters;
- empty/invalid/overlong regex → `INVALID_ARGUMENT` before Telegram work;
- max pattern length 512;
- regex + case-sensitive state are cursor-query-bound;
- changed regex with old cursor → `INVALID_CURSOR`;
- legacy schema rejects regex;
- packaged standalone + portable search-filter smoke covers both regex and url-domain.

# Final automated runtime candidate

The final runtime-affecting head currently frozen for acceptance is:

```text
runtime head: 5c143c74907f8e8b243df8065c895654983b2fd2
Windows PR run: 33310905962
result: SUCCESS
full pytest: 140 passed in 2.05s
focused v0.3.1 regressions: 45 passed in 0.71s
compileall: PASS
git diff --check: PASS
GUI + daemon + reader + CLI imports: PASS
source search-filter smoke: PASS
one-file GUI build: PASS
portable GUI build: PASS
tgctl build: PASS
packaged standalone + portable domain+regex smoke: PASS
packaged standalone + portable SESSION_BUSY JSON/native exit=8: PASS
packaged GUI/tgctl smoke: PASS
tracked worktree clean gate: PASS
candidate asset preparation/upload: PASS
```

Candidate artifact:

```text
id: 9731995716
name: TGExporter-v0.3.1-candidate-windows-x64
URL: https://github.com/3ll3-3ll3/tg-exporter/actions/runs/33310905962/artifacts/9731995716
outer Actions artifact ZIP SHA-256:
96ea4c364160f5f8043ecbf1ec2fa9addc1f4db12aa28038ee7716655489d88c

TGExporter-v0.3.1-windows-x64.exe
bf6d9eebbc02636760b4c959769c759fc5fea446967b64a7b5cadb629777b681

TGExporter-v0.3.1-windows-x64-portable.zip
2a7947c30ec92a180b0f446562ee86bc486f01619b888a47210399744af5e1f8

tgctl.exe
1af365a7af3a5b5c80047fdfdf643d8584d8155dc8312909af66e89aed982a6b
```

These are Candidate hashes only, not formal Release hashes. Any formal `v0.3.1` Release must be rebuilt from the eventual merged final `main` by the Release workflow; never reuse or overwrite `v0.3.0`.

The branch contains documentation commits after the frozen runtime head. The **final PR head must still receive one complete green Windows CI** before merge; once that final docs-head run is green, record it in PR #24 without another branch commit so the head does not move again.

# Remaining human/local acceptance

Automated CI is complete but cannot prove behavior against the user's real Windows `%APPDATA%` state or authorized Telegram account. Before calling v0.3.1 release-ready, verify locally without forbidden writes:

1. packaged `tgctl.exe` real-chat domain + regex searches;
2. idle GUI close;
3. refresh groups then close;
4. 0-message current-unread export with mark-read disabled, then close;
5. two GUI instances started together and closed one by one;
6. `tgctl status` remains usable after each GUI closes and shared daemon remains alive;
7. new `app.log` segment has zero normal-close Fatal/Traceback/un-awaited-coroutine/Task-destroyed entries;
8. re-run the same bounded sender sample used for the v0.3.0 finding and report before/after counts only, with no real message bodies/URLs/IDs;
9. privacy audit reports counts only, never sensitive log lines.

If any check would require real send/forward, mark-read, confirmed media download, group mutation, FloodWait stress, or Session reset, stop and obtain separate explicit authorization.

# Current workflow

1. allow this documentation update to finish one final PR-head Windows CI;
2. do not move branch head again if that CI passes;
3. keep PR #24 Draft until local human checks pass;
4. after human PASS + explicit user authorization, mark Ready and merge through PR;
5. only after merge prepare a **new** `v0.3.1` tag/Release; never alter `v0.3.0`.

# New Chat Resume Instructions

Read in order:

1. `AGENTS.md`
2. `HANDOFF.md`
3. `README.md`
4. `docs/CODEX_TGCTL.md`
5. `docs/releases/v0.3.0.md`
6. `docs/releases/v0.3.1.md`
7. architecture/security/testing/release docs as needed

Then verify GitHub current `main`, formal `v0.3.0`, branch `codex/v0.3.1-runtime-fixes`, PR #24, and the latest Windows CI. GitHub facts override this snapshot.
