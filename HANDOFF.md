# HANDOFF.md

> 当前项目交接快照。新 Agent / GPT 接手时先读 `AGENTS.md`，再读本文件；完成恢复检查前不要修改代码。

# Current Project State

**Last updated:** 2026-08-30 13:50 +08:00  
**Repository:** `3ll3-3ll3/tg-exporter`  
**Default branch:** `main`  
**Production version:** `v0.1.10`  
**Production commit/tag:** `cedb02035597aa607fac399666154519f480c431` / `v0.1.10`  
**Current development version:** `v0.3.0` Candidate  
**Current development branch:** `codex/personal-account-reader-v0.3.0`  
**Current development branch tip:** `7282326e3ce51a294b90840e9cf7c965ad304fc7`  
**Frozen runtime candidate:** `0ad4219ef367d28326b5aca705fffe1d007db52b`  
**Current task:** 先修 KI-001 current-unread snapshot timing mismatch，再做 v0.3 真实 Telegram E2E  
**Related Issue:** 无独立 Issue；当前实现由 PR 驱动  
**Related PR:** Draft PR #20 `feat: v0.3.0 personal account reader candidate`  
**Release gate:** PR #20 不 merge；不创建/覆盖 `v0.3.0` Release，直到 KI-001 修复 + 真人 E2E PASS + 用户明确发布授权

## Source of truth

`main` 是当前正式 Production 线，不是最新开发代码。v0.3 daemon/reader/runtime 在 PR #20 分支。

历史 Draft PR：

- #17 `docs: design single Telegram daemon + local IPC`：v0.2 设计依据，已被实现吸收；
- #19 `docs: design v0.3.0 personal account reader`：v0.3 设计依据，已被 #20 实现；
- #20：唯一当前实现/验收入口。

旧 `docs/agent-handoff` 分支不是当前 handoff 主线。

# Project Summary

TG Exporter / TG 导出器是 Windows 本地 Telegram 工具：

1. GUI：多群独立导出文字/caption 到 JSON；
2. `tgctl`：供 Codex/命令行列聊天、搜消息、取消息，并在安全边界内 true-forward / 纯文本 send；
3. v0.2/v0.3：single daemon 唯一持有 Telegram Session，GUI/tgctl 走本地 IPC；
4. v0.3 Personal Account Reader：分页读取账号、全部 dialogs、成员/管理员、rich messages、Forum、Saved Messages、media metadata；显式媒体下载采用两阶段确认。

不是 Telegram Desktop 替代品、累计数据库、云服务、Bot API 产品或 24/7 自主 Agent。

# Production Definition

本项目没有远程生产数据库、云端服务或服务器部署。

Production = GitHub 正式 Release Windows 二进制 + 用户本机 `%APPDATA%\TelegramMultiChatExporter\` + 用户真实 Telegram 账号 + 用户导出目录。

不要机械套用远程 DB migration/Secret Manager/Cloud rollback 思路。

# Production Version

Latest Release：**v0.1.10**，target `cedb02035597aa607fac399666154519f480c431`。

Release：`https://github.com/3ll3-3ll3/tg-exporter/releases/tag/v0.1.10`

```text
TGExporter-v0.1.10-windows-x64.exe
sha256 b598aecdd7fcc3f5731ba955f7f02d8bd45ea47220f66a040bc20b64f4e410be

TGExporter-v0.1.10-windows-x64-portable.zip
sha256 113c6f8223d6f648571bf8ad3e86a1df1db2ad1e118bb2674e70f0031b0274dd

tgctl.exe
sha256 ebd6cd8898f51aa9e63a7efa6292a70df0afe15cd5efe99b7fc4be9bbf2f5efa
```

v0.1.10 修复 packaged Windows 非 UTF-8 console 下中文 JSON `UnicodeEncodeError`，恢复 `SESSION_BUSY` native exit=8。该修复/回归已 forward-port 到 v0.3 Candidate。

# Current Architecture

## Production v0.1.10

```text
GUI ─┐
     ├→ direct TelegramService/Telethon → one SQLiteSession
 tgctl┘
```

GUI/tgctl 用 OS `SessionLease` 互斥；不得绕锁/复制 Session。

## Candidate v0.3

```text
GUI ─┐
     ├→ authenticated Windows Named Pipe + UTF-8 JSON → TG daemon → TelegramService/Telethon → one Session
 tgctl┘
```

Daemon 是唯一 Session owner。同代 GUI+tgctl 正常共存；`SESSION_BUSY` 只用于旧 direct process 已锁 Session 的兼容边界。

```text
LOCAL status/job/heartbeat       → immediate
export                           → exclusive Telegram job
reader                           → waits during export
real send/forward during export  → EXPORT_IN_PROGRESS, never queued
```

完整说明见 `docs/ARCHITECTURE.md`、ADR 和 PR #20 分支设计文档。

# Completed

## Stable v0.1.x

- Windows GUI 多群独立 JSON；
- focused workspace / Telegram Folder / avatar lazy load；
- software-managed Export Category + `category/group/timestamp.json`；
- Basic Group→Supergroup catalogue collapse + date-range legacy history；
- current-unread / since-last / Option B read ack；
- Windows system proxy；
- qasync modal/shutdown fixes；
- tgctl status/chats/search/get/forward/send、JSON contract、dry-run、20/200 cap、AMBIGUOUS_CHAT、FloodWait；
- v0.1.9 真人 Saved Messages send/forward E2E；
- v0.1.10 packaged UTF-8/exit-code hotfix Release。

## v0.2 inherited by v0.3

`codex/single-daemon-v0.2.0 @ 165b0a86c85049cb25ab51f601c210ef986556a2`：single daemon、Named Pipe IPC、GUI/tgctl clients、tray、lease/heartbeat、daemon-side export、operation coordinator、idle shutdown、write scheduling。未单独正式 Release；v0.3 继承。

## v0.3 Candidate主体

PR #20 已实现：

```text
tgctl account get
tgctl dialogs list
tgctl chats get/chats members
tgctl messages history/search/get
tgctl topics list/history
tgctl media download
```

Reader：default page 100 / max 500、HMAC/query-bound safe cursor、rich MessageInfoV3、current-role semantics、anonymous/send-as no inference、migration current→legacy、hostname domain filter、Forum、metadata-only media + explicit two-stage download。

## Pre-E2E tail audit fixed

- restored standalone+portable packaged `SESSION_BUSY JSON/native exit=8` release gate；
- release import gate includes daemon+reader+tgctl；
- retained v0.1.10 cp1252/UTF-8 source regression/session lock helper；
- fixed migrated global search legacy cursor duplicate/gap bug；
- added single-chat migrated cursor segment/stale semantics；
- migrated history role snapshot uses current logical Supergroup；
- rich-get legacy source returns current logical `chat_id` + legacy `source_chat_id`；
- Candidate CI expanded one-file + portable；
- `main@v0.1.10` integrated into #20 ancestry and PR retargeted to main；
- no unresolved PR #20 review thread at audit time。

# Frozen v0.3 Candidate

The current pre-KI-001 frozen runtime remains traceable, but **must not be considered final release candidate until KI-001 is fixed**:

```text
runtime commit: 0ad4219ef367d28326b5aca705fffe1d007db52b
Windows run: 33293667296 = success
pytest: 91 passed
artifact: 9726786295
URL: https://github.com/3ll3-3ll3/tg-exporter/actions/runs/33293667296/artifacts/9726786295
```

```text
one-file EXE sha256 94f43dadc421e67de0a5f8cb7d1ff0b3f98bb85e46a46ca423c9d7d025fc55c6
portable ZIP sha256 6d0dad9514eab1ff1c4d80b35df704951fc7fe63ff23bea2536dcf01c19626bc
tgctl.exe sha256 aee8edbe9c7693b3fa299757bc386b285c42003e03d787718903b7223ae638a0
outer artifact sha256 37309a137577f8aa3de63bc5ff2a188147b1908be5d4e7a0e53df531358503f7
```

PR branch tip `7282326e...` was docs-only after runtime; Windows run `33294055220` also success.

# In Progress

1. **Fix KI-001** (current-unread snapshot timing) on PR #20 runtime branch；
2. add regression tests and rerun full Windows Candidate gate；
3. freeze a new Candidate hash；
4. then run user real-account E2E。

Do not add unrelated features, merge #20, or release v0.3 while this is pending.

# Pending

After KI-001 fix, human E2E should cover:

- all dialog types + Telegram Folder；
- real 500-message history；
- owner/admin, sender/current role, domain filters；
- anonymous/send-as identity safety；
- pagination/search no overlap/gap；
- since/until；
- Saved Messages；
- MESSAGE_NOT_FOUND / AMBIGUOUS_CHAT；
- v0.3 GUI + tgctl coexist；
- legacy direct lock → SESSION_BUSY + exit 8；
- GUI safe legacy-lock diagnostic；
- log/stdout safety；
- Forum if available；
- media metadata-only no files；
- media plan creates no dir/files；
- real media confirm only if user explicitly chooses。

Do not intentionally trigger FloodWait. Default E2E does not repeat send/forward/mark-read; real write re-test still requires dry-run + user confirmation.

# Known Bugs

## KI-001 — Current-unread snapshot timing mismatch (OPEN)

**Confirmed by code audit 2026-08-30.** Full details: [`docs/KNOWN_ISSUES.md`](docs/KNOWN_ISSUES.md).

User-confirmed intended semantics:

```text
for each group, when that group's export begins:
freeze read_inbox_max_id + latest_message_id
export read_inbox_max_id < id <= latest_message_id
optional read ack only through that frozen latest id
```

Current runtime instead uses `GroupInfo` state captured when catalogue was loaded/refreshed. `exporter.py` explicitly comments this behavior; `ExportCoordinator` passes the serialized plan without per-group read-state refresh.

This is an existing correctness mismatch, not a new feature request. It should be fixed before final v0.3 E2E/release.

Historical fixed bugs retained as regression knowledge:

- qasync blocking modal → task re-entry；
- cp1252 Chinese JSON → error handler UnicodeEncodeError → native exit 1；
- migrated global search legacy cursor duplicate/gap；
- migrated rich-get logical/source ID mismatch。

# Known Risks

- no branch protection; PR/no-force-main discipline is policy, not GitHub enforcement；
- v0.3 still lacks systematic real-account E2E；
- Telegram cannot prove historical admin tenure/hidden anonymous identity/deleted status; return unknown/unavailable rather than guess；
- media download is local-disk side effect and needs explicit confirmation；
- old direct binary and daemon can intentionally hit SessionLease compatibility boundary；
- historical Draft PR #17/#19 remaining open can confuse future agents；
- frozen pre-KI-001 Candidate hashes remain useful for traceability but must be replaced after runtime fix。

# Technical Debt

- v0.2 was implemented but never separately released; v0.3 directly inherits it；
- detailed v0.3 design remains in PR #20 branch until merge; main handoff/ADRs must remain sufficient for discovery；
- historical `docs/DECISIONS.md` was monolithic; critical decisions now have ADRs；
- MCP remains future direction only；
- KI-001 demonstrates that old docs used catalogue-refresh unread semantics while the confirmed product requirement is export-start semantics; docs/tests/runtime must be aligned after fix。

# Important Constraints

- keep `%APPDATA%\TelegramMultiChatExporter\`；
- do not delete historical JSON when categories/settings change；
- do not bypass/copy Telegram Session locks；
- do not infer migration by same name；
- do not infer anonymous admin identity from display text；
- do not call missing messages deleted without proof；
- reader must not implicitly mark-read/write；
- Actions Artifact is not Production；
- 360/AV false-positive/code-signing work is currently deprioritized。

# Production Safety Boundaries

- no Secret/Session content in repo/log/CI；
- no AppData migration/deletion as maintenance shortcut；
- no direct/force push main；
- no tag/Release overwrite/delete；
- no real Telegram send/forward/mark-read without explicit authorization；
- media confirm download only when user explicitly chooses；
- no daemon TCP/HTTP/Web exposure；
- no real Telegram credential in GitHub Actions。

See `docs/SECURITY_MODEL.md` and `SECURITY.md`.

# Recent Decisions

Critical ADRs:

- ADR-001 single daemon owns Session；
- ADR-002 authenticated Named Pipe + UTF-8 JSON bytes；
- ADR-003 bounded reader + HMAC/query-bound cursor；
- ADR-004 bounded explicit Telegram writes, no replay after unknown outcome；
- ADR-005 one logical current Supergroup + legacy historical source；
- ADR-006 human E2E + explicit user authorization before v0.3 release。

# Next Steps

1. On PR #20 branch, fix KI-001 to snapshot unread state at **each group's export start**；
2. add tests: stale catalogue vs newer export-start snapshot, post-snapshot arrival excluded, ack exact upper bound, multi-group separate snapshots；
3. run full Windows CI one-file+portable+tgctl/package gates；
4. freeze new runtime commit/artifact/hashes and update HANDOFF/PR；
5. run real Telegram E2E；
6. fix only actual E2E failures + revalidate affected scenarios；
7. after all PASS, user explicitly authorizes `v0.3.0` release；
8. finalize release notes → merge/release → verify tag/target/assets/SHA256/workflow → update HANDOFF Production state。

# Recommended Next Task

**KI-001 correctness fix, not a new feature.** Do that before asking the user to spend time on full real-account E2E.

# How To Resume

1. Recheck GitHub Latest Release/main；
2. recheck PR #20 OPEN/DRAFT/base/head/checks；
3. read `docs/KNOWN_ISSUES.md`；
4. inspect current PR #20 `exporter.py`, `read_state.py`, `export_coordinator.py` for KI-001；
5. read PR #20 design docs and ADRs；
6. do not modify unrelated code；
7. if KI-001 has already been fixed by a newer commit, verify regression/CI/new frozen artifact and update this HANDOFF before continuing E2E。

# New Chat Resume Instructions

Before editing code, a new GPT must:

1. read `AGENTS.md`；
2. read `HANDOFF.md`；
3. read `README.md`；
4. read `docs/KNOWN_ISSUES.md`；
5. read `docs/ARCHITECTURE.md`；
6. read `docs/SECURITY_MODEL.md` + `SECURITY.md`；
7. read `docs/TESTING.md`, `docs/DEPLOYMENT.md`, `docs/RELEASE_PROCESS.md`；
8. read relevant `docs/decisions/` ADRs；
9. inspect PR #20 and distinguish historical #17/#19；
10. verify main/dev branch commits, CI, Latest Release/Tags。

Then report to the user **before making changes**:

- current project state；
- current task；
- current known bug/risk；
- recommended next action。

If repository facts differ from this snapshot, GitHub wins; update HANDOFF first.