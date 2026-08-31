# HANDOFF.md

> 当前开发/发布交接快照。任何 Agent 接手前先读 `AGENTS.md`，再读本文件；GitHub 当前事实优先。

更新时间：2026-08-31

# Current Project State

- Repository: `3ll3-3ll3/tg-exporter`
- Current Production: **v0.3.1**
- Production commit/tag: `38b5687038f5ac458571a65820744a7bd325564f` / `v0.3.1`
- Formal Release: `https://github.com/3ll3-3ll3/tg-exporter/releases/tag/v0.3.1`
- Current patch branch: `codex/v0.3.2-sender-role-fix`
- Patch purpose: a small sender-identification / `--sender-role` filtering fix on top of v0.3.1. It is **not** a broad reader redesign.
- Do not move, overwrite, delete or rebuild the existing v0.3.1 tag/Release in place.
- This branch may produce CI Candidate artifacts only. Do not publish a Release unless separately authorized.

# Why this patch exists

Some real supergroup messages can expose Telegram sender evidence through raw peer fields even when the sender entity is not hydrated. v0.3.1 could still leave those rows as `sender_type=unknown`, which also caused `tgctl messages search --sender-role admin ...` to miss some current admin/owner/anonymous/send-as sources.

The patch is intentionally narrow:

1. before returning `unknown`, inspect existing Telethon message sender evidence including `sender_id`, `sender`, `from_id`, `peer_id`, `sender_chat`, `post_author` and explicit anonymous-admin indicators;
2. only while a `messages.search` request uses `--sender-role`, allow bounded sender-entity recovery;
3. cache sender resolution per search request, including failed lookups, so the same peer is never resolved once per message;
4. classify Telegram-explicit anonymous administrator as `anonymous_admin`, `anonymous_admin=true`, `is_admin=true`, without guessing a user id;
5. classify Telegram-explicit current-chat send-as with `posted_as_chat_id=<current chat>` and allow it to match the admin role without claiming a specific owner/admin identity;
6. keep `forward_origin` separate from the actual sender; a forwarded admin is not an actual admin sender;
7. a textual `post_author` alone is not identity evidence;
8. messages with no sender evidence remain `unknown`.

# Performance / safety invariants

```text
TGExporter GUI ─┐
               ├─ authenticated Windows Named Pipe → TG daemon → Telethon → one user Session
tgctl / Codex ─┘
```

- daemon remains the normal single Telegram Session owner;
- GUI/tgctl do not fall back to direct SQLiteSession;
- ordinary GUI/manual export does not enter sender-role recovery mode and gains no new identity network requests from this patch;
- ordinary history and search without `--sender-role` do not enable the patch's request-local entity resolver;
- only `--sender-role` may read one current admin snapshot and perform bounded/cached sender resolution;
- current-unread, Session ownership, IPC, daemon lifecycle, GUI export format/directories and media behavior are unchanged;
- reader remains bounded and default read-only;
- this patch does not authorize real send/forward, mark-read, media download confirmation, group mutation, FloodWait stress or Session reset;
- ordinary logs/Issues/PRs must not expose API hash, phone/OTP/2FA, Session contents, IPC secret, access hash/file reference, message body/caption/URL/media filename.

# Automated evidence before documentation closeout

Green branch-head runtime validation:

```text
head: c79ef449d29a89e520d9d9a74bd267b277b62e20
Windows run: 33369455891 = SUCCESS
full pytest: 147 passed in 2.07s
focused v0.3.1 regressions: 45 passed in 0.60s
compileall: PASS
git diff --check: PASS
imports: PASS
source search-filter smoke: PASS
one-file GUI build: PASS
portable GUI build: PASS
tgctl build: PASS
packaged search-filter smoke: PASS
packaged SESSION_BUSY JSON/native exit=8: PASS
packaged GUI/tgctl smoke: PASS
tracked-worktree clean: PASS
```

Candidate artifact from that runtime head:

```text
artifact: 9749607042
outer artifact ZIP SHA-256: 31437efc25d573452a77c0f604805533b0a8adc8dea1792024d0877fabdd8510
TGExporter-v0.3.1-windows-x64.exe: 74af0ebe0805a445849c39cf8bbb8240f5a2f9a48875c7e122f1bc8229c40601
TGExporter-v0.3.1-windows-x64-portable.zip: 0dbc5194b6aa23a4be3da076b2638fd22ba662bcaefbb2aa31f686d26c0f1f37
tgctl.exe: 0fd0bc8c51dd502b9ff52f10fcdb6777f4f2823e781a07e0f64438675482e08d
```

These are Candidate hashes only. Documentation commits after this snapshot require a new final branch/PR-head CI; report hashes from the final green head, not these earlier values.

# Real Telegram check still recommended

The patch has not been validated against the user's live Svip sample from this environment. A post-patch **read-only** bounded comparison is recommended after the final Candidate is fixed:

```powershell
tgctl messages search --chat <Svip-ref> --sender-role admin --url-domain mypikpak.com --limit 500 --json
```

Only compare aggregate counts such as total matches and sender categories. Do not print real message bodies/URLs/media names into Issues/PRs/logs. No write action or media download is needed.

# Resume order

Read `AGENTS.md` → `HANDOFF.md` → `docs/CODEX_TGCTL.md` → verify GitHub `main`, latest Release, current patch branch/PR and latest workflow. GitHub facts override this snapshot.
