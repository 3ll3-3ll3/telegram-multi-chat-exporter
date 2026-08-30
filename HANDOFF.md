# HANDOFF.md

> 当前开发交接快照。任何 Agent 接手前先读 `AGENTS.md`，再读本文件；在核对 GitHub 当前事实前不要修改代码。

更新时间：2026-08-30

# Current Project State

- Repository: `3ll3-3ll3/tg-exporter`
- Production version: **v0.1.10**（直到正式 v0.3.0 GitHub Release 实际创建并核验前仍以此为准）
- Production commit/tag: `cedb02035597aa607fac399666154519f480c431` / `v0.1.10`
- Current development version: **v0.3.0 release candidate**
- Development branch: `codex/personal-account-reader-v0.3.0`
- Implementation PR: **#20**, base `main`
- Issue #22: **fixed + closed**
- Frozen runtime Candidate accepted by user: `7e6f62d0c12eb9f88e53a15a5daaa271ba61e68c`
- Windows Candidate run: `33296790070 = success`
- pytest: **95 passed**
- Candidate artifact: `9727721868`
- Human acceptance: **PASS declared by user on 2026-08-30; no new runtime defect reported in that acceptance step**
- Current task: **formal v0.3.0 release only; do not add new features**

## Project Summary

TG Exporter / TG 导出器是 Windows 本地 Telegram 工具：

1. GUI：按群独立导出文字/caption JSON；
2. `tgctl`：供 Codex/命令行查询 Telegram，并在既有安全边界内 true-forward / 纯文本 send；
3. v0.2/v0.3：single daemon 是唯一 TelegramClient/Session owner，GUI/tgctl 通过 authenticated Windows Named Pipe JSON IPC；
4. v0.3 Personal Account Reader：分页读取账号、dialogs、成员/管理员、rich messages、Forum、Saved Messages、media metadata，并提供显式两阶段本地媒体下载。

不是 Telegram Desktop 替代品，不是云服务/数据库，不是 Bot API，也不是 24/7 自主 Agent。

## Production Definition

本项目没有远程生产数据库/服务器。Production 指：

- GitHub 正式 Release Windows 二进制；
- 用户本机 `%APPDATA%\TelegramMultiChatExporter\` 下真实 Session/API/settings/checkpoint/log/cache；
- 用户真实 Telegram 账号和本地导出文件。

正式 v0.3.0 Release 实体和资产未核验前，不得把 Production 从 v0.1.10 改成 v0.3.0。

## Current Architecture

```text
TGExporter GUI ─┐
               ├─ authenticated Named Pipe / UTF-8 JSON → TG daemon → Telethon → one user Session
tgctl / Codex ─┘
```

v0.3 daemon 规则：

```text
LOCAL status/job/heartbeat       → immediate
export                           → exclusive Telegram job
Telegram reader                  → waits while export active
real send/forward during export  → EXPORT_IN_PROGRESS, never queued for later
explicit media download          → bounded local-disk side effect
```

GUI/tgctl 不得 fallback direct SQLiteSession。`SESSION_BUSY` 只用于 legacy/direct process 已占用 SessionLease 的兼容边界，packaged native exit code 必须保持 8。

## GUI Export Invariants

- 输出：`output_root / Export Category / group / YYYY-MM-DD_HH-mm-ss.json`；同秒 `_2/_3/...`；
- 每群每次 JSON 独立，不读取/合并/覆盖历史；
- Export Category 是本地分类，不是 Telegram Chat Folder；
- 默认只导出文字/caption，不下载消息媒体；头像仅 UI cache；
- Basic Group→Supergroup catalogue 只显示 current logical group；legacy 只用于历史兼容；
- qasync async flow 禁止重新引入 blocking nested modal；
- 兼容数据目录固定 `%APPDATA%\TelegramMultiChatExporter\`。

### Current unread — Issue #22 fixed semantics

每个群在**该群真正开始执行导出时**单独冻结：

```text
lower = read_inbox_max_id_at_group_start
upper = latest_message_id_at_group_start
export only lower < id <= upper
```

- 不再使用 catalogue refresh 时的旧 snapshot；
- snapshot 后新到消息不属于本次 run；
- optional read-ack 必须使用与 export 完全相同的 frozen upper；
- `JSON atomic success → checkpoint → optional read ack`；
- export failure 不 read-ack；read-ack failure 不删除已成功 JSON；
- migrated current-unread 只刷新 current logical Supergroup，legacy Basic Group 不参与。

实现：`src/telegram_exporter/unread_snapshot.py` + daemon `ExportCoordinator` per-group execution plan copy。

## v0.3 Reader Completed

```text
tgctl account get
tgctl dialogs list
tgctl chats get
tgctl chats members
tgctl messages history
tgctl messages search
tgctl messages get
tgctl topics list
tgctl topics history
tgctl media download
```

关键语义：

- dialogs 覆盖 group/supergroup/channel/private/bot/Saved/archive/forum/folder safe metadata；
- reader 独立模型，不破坏 GUI GroupInfo；
- default page 100 / max 500；HMAC/query-bound cursor，不含 access_hash/file_reference；
- rich MessageInfoV3：sender/reply/forward/entities/reactions/poll/service/media 等；
- current sender-role，不伪造历史管理员身份；anonymous/send-as 不反推个人；
- migration logical history current→legacy，唯一定位 `(source_chat_id,message_id)`；
- URL domain 使用真实 hostname parser；
- Forum；
- media 默认 metadata-only；显式 download = plan→confirmation→download + hard caps + `.part` atomic rename。

Existing `status/chats list/messages search/messages get/forward/send` 继续兼容。send/forward 安全边界继续是 true forward、plain text、dry-run、20/200 cap、AMBIGUOUS_CHAT、FloodWait structured stop、unknown-outcome no retry、no-body logging。

## Pre-Release Tail Audit / Fixes Completed

1. Release workflow 恢复 standalone + portable `SESSION_BUSY JSON/native exit=8` gate；
2. v0.1.10 UTF-8/cp1252 regression 完整前移；
3. migrated global advanced-search legacy cursor duplicate/gap bug 已修；
4. single-chat migrated cursor / `CURSOR_STALE` 已加固；
5. legacy history role 使用 current logical Supergroup；
6. migrated rich-get logical/source IDs 一致；
7. Candidate gate 包含 one-file + portable；
8. `main@v0.1.10` 已纳入 PR #20 ancestry，PR base=`main`；
9. Issue #22：current-unread 改为 per-group export-start snapshot，并补回归；
10. migrated legacy peer 不会污染 current-unread snapshot；
11. PR #20 无未解决 inline review thread；
12. `docs/releases/v0.3.0.md` 已从 Candidate Notes 收尾为正式 Release Notes。

## Frozen Human-Accepted Candidate

```text
runtime candidate head: 7e6f62d0c12eb9f88e53a15a5daaa271ba61e68c
Windows PR CI run: 33296790070
result: success
pytest: 95 passed in 2.19s
one-file build: success
portable build: success
tgctl build: success
standalone SESSION_BUSY JSON/native exit 8: success
portable SESSION_BUSY JSON/native exit 8: success
one-file + portable GUI smoke: success
standalone + portable tgctl smoke: success
artifact upload: success
```

Artifact：

```text
id: 9727721868
name: TGExporter-v0.3.0-candidate-windows-x64
URL: https://github.com/3ll3-3ll3/tg-exporter/actions/runs/33296790070/artifacts/9727721868
outer artifact ZIP SHA-256:
f68ea1d7b711f51c122a972008a32f1ffa06355ba1c85bdc9bd870e4fb67caca

TGExporter-v0.3.0-candidate-windows-x64.exe
0afccfe03c005b78ad90aefd904f75fa53f536f22f7d90a90f00f1928fd403ae

TGExporter-v0.3.0-candidate-windows-x64-portable.zip
5fae791e3e8a87bafcfc4b17256349d1945787b163d4114a01bed05fadb9f7e8

tgctl.exe
01e566de4cc95fff273b68e4039b346843e2b3c54ee8f4afb74e9fe7a50189d5
```

Candidate Artifact 仅用于发布前验收，不是正式分发物。正式资产必须由 Release workflow 从最终 main commit 重新构建，并以正式 `SHA256SUMS.txt` 为准。

## Human Acceptance

2026-08-30 用户明确确认第三版验收通过，并要求继续下一步工作。本次确认未报告新的 runtime defect。

项目流程上 human acceptance gate 已满足；仍必须完成：final PR CI → Ready → merge `release: v0.3.0` → formal Release workflow → Release/tag/assets/hash 核验。

## Known Risks / Technical Debt

- `capture_current_unread_snapshot()` 当前通过 `iter_dialogs()` 精确查 current chat，正确性优先；大量 dialogs + 大批群时可能有 O(groups × dialogs) 延迟，可在 v0.3.0 发布后单独优化，不在本次 Release 临时重构；
- branch protection 不是 GitHub 强制时，Agent 必须自行遵守 PR/no-force-push/no-release-overwrite；
- Telegram 权限/历史可见性会因真实账号而异，unavailable 不得伪造；
- Candidate 与正式 Release 是两次独立构建，正式资产 hash 预期可能与 Candidate 不同。

## Current Release Steps

```text
1. final PR #20 head CI PASS
2. mark PR #20 Ready
3. merge with commit title/message starting `release: v0.3.0`
4. wait formal Release workflow
5. require pytest/import/build/SESSION_BUSY/smoke/assets all PASS
6. verify GitHub Release `v0.3.0` actually exists
7. verify tag/target commit and four assets
8. verify SHA256SUMS.txt / asset digests
9. only then update HANDOFF production state to v0.3.0
```

不得覆盖/删除旧 tag 或 Release。若 Release workflow 失败，先修失败，不对外声称已发布。

# New Chat Resume Instructions

新的 GPT 接手时：

1. 读 `AGENTS.md`；
2. 读本 `HANDOFF.md`；
3. 读 `docs/PERSONAL_ACCOUNT_READER_V3_DESIGN.md`、`docs/ARCHITECTURE.md`、`docs/DECISIONS.md`、`docs/TESTING.md`、`SECURITY.md`、`docs/releases/v0.3.0.md`；
4. 核对 PR #20 当前状态/head/CI；
5. 核对 Issue #22 为 closed；
6. 核对 Latest Release；
7. 若 v0.3.0 Release 已存在，必须核验 target/assets/SHA 后再把它当 Production；
8. 在这些核对完成前不要修改新功能。

恢复后先输出：当前 Production、发布流程状态、风险和下一步。GitHub 当前事实若与本文件冲突，以 GitHub 为准并更新 HANDOFF。
