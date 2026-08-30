# HANDOFF.md

> 当前开发/发布交接快照。任何 Agent 接手前先读 `AGENTS.md`，再读本文件；GitHub 当前事实优先。

更新时间：2026-08-30

# Current Project State

- Repository: `3ll3-3ll3/tg-exporter`
- Current Production before this release completes: **v0.3.0**
- Production commit/tag: `8e230e33ea928bcf71296e4e5379b097446dbec5` / `v0.3.0`
- Release target: **v0.3.1**
- Branch: `codex/v0.3.1-runtime-fixes`
- PR: **#24**
- v0.3.0 tag/Release must never be moved, overwritten, deleted or rebuilt in place.

## Explicit v0.3.1 release authorization

On 2026-08-30 the user explicitly instructed: publish the current v0.3.1 as a formal Release **without waiting for the remaining real Windows / real Telegram human E2E**.

Record this accurately:

- human E2E is **WAIVED for v0.3.1 only**;
- it is **not PASS** and must never be reported as PASS;
- automated CI/package gates are green;
- residual real-environment risk is knowingly accepted for this release;
- future releases return to the default human-E2E gate unless the user explicitly waives it again.

# Why v0.3.1 exists

v0.3.1 fixes four main v0.3.0 acceptance findings without expanding Telegram write permissions:

1. packaged `tgctl messages search --url-domain ...` could fail during frozen IDNA normalization;
2. normal GUI close could hit `RuntimeError: Event loop stopped before Future completed`;
3. sender/owner diagnostics were too coarse for real bounded samples;
4. the required acceptance matrix included regex search but v0.3.0 had no regex parameter.

# Runtime / safety invariants

```text
TGExporter GUI ─┐
               ├─ authenticated Windows Named Pipe → TG daemon → Telethon → one user Session
tgctl / Codex ─┘
```

- daemon remains the normal single Telegram Session owner;
- GUI/tgctl do not fall back to direct SQLiteSession;
- GUI close detaches its own lease and must not kill the shared daemon;
- reader remains bounded and default read-only;
- ordinary reader media behavior remains metadata-only;
- real send/forward keep dry-run/caps/no-auto-retry semantics;
- current-unread keeps the per-group export-start frozen snapshot invariant;
- ordinary logs/Issues/PRs must not expose API hash, phone/OTP/2FA, Session content, IPC secret, access hash/file reference, message body/caption/URL/media filename.

# v0.3.1 automated evidence

Final green PR-head Candidate before the authorization-only release documentation update:

```text
head: e5ebe531ad132d5b501e014ab8616b48119f2bec
Windows PR run: 33311934536 = SUCCESS
full pytest: 140 passed in 1.90s
focused v0.3.1 regressions: 45 passed in 0.58s
compileall: PASS
git diff --check: PASS
imports: PASS
source search-filter smoke: PASS
one-file GUI build: PASS
portable GUI build: PASS
tgctl build: PASS
packaged standalone + portable domain+regex smoke: PASS
packaged standalone + portable SESSION_BUSY JSON/native exit=8: PASS
packaged GUI/tgctl smoke: PASS
tracked-worktree clean: PASS
```

Candidate artifact from that head:

```text
artifact: 9732308884
outer ZIP SHA-256: 7cb2931602ff8cf2d3e7223c33c0920f81a3e12faa589a34f471ec545f9cfb88
TGExporter-v0.3.1-windows-x64.exe: 25b66f41622ef79634b1e13de30d7271d507939ae040b36c7aa9fd937c461ebf
TGExporter-v0.3.1-windows-x64-portable.zip: ad4db31f4aa21adae7d8c19457325e44569f883f39e59cb701760953a79bb4ca
tgctl.exe: cb539add525fdc899629d492429bc0436ee63af789acf33f95a00ae4c9f9ba34
```

These are Candidate hashes only. Formal Release must be rebuilt from merged `main`.

# Human/local checks not performed before v0.3.1 release

Because the user explicitly waived them for this release, these remain **unverified**, not failed and not passed:

- packaged real-chat domain + regex search;
- idle/refresh/zero-unread real GUI close scenarios;
- two real GUI instances closed sequentially with daemon/tgctl survival;
- new real `app.log` segment counts for Fatal/Traceback/un-awaited/Task-destroyed;
- post-fix real bounded sender aggregate counts.

No real send/forward, mark-read, confirmed media download, group mutation, FloodWait stress or Session reset was performed as part of this release authorization.

# Current release workflow

1. commit this one-release waiver + final release notes/workflow hardening on PR #24;
2. require one final green PR-head Windows CI;
3. mark PR #24 Ready;
4. merge to main with release commit message `release: v0.3.1`;
5. formal Release workflow rebuilds from merged main;
6. verify `v0.3.1` tag target, Release state, four assets and SHA256SUMS;
7. do not alter v0.3.0.

# Resume order

Read `AGENTS.md` → `HANDOFF.md` → `README.md` → `docs/KNOWN_ISSUES.md` → `docs/releases/v0.3.1.md` → architecture/security/release docs. Then verify GitHub current main, latest Release, PR #24 and latest workflow. GitHub facts override this snapshot.
