# HANDOFF.md

> 当前开发交接快照。任何 Agent 接手前先读 `AGENTS.md`，再读本文件；在核对 GitHub 当前事实前不要修改代码。

更新时间：2026-08-30

# Current Project State

- Repository: `3ll3-3ll3/tg-exporter`
- Production version: **v0.1.10**
- Production commit/tag: `cedb02035597aa607fac399666154519f480c431` / `v0.1.10`
- Current development version: **v0.3.0 Candidate**
- Development branch: `codex/personal-account-reader-v0.3.0`
- Implementation PR: **#20**, `OPEN + DRAFT`, base `main`
- Issue #22: **runtime fix completed and Candidate gate passed**; close after final GitHub status sync
- Frozen runtime Candidate for human E2E: `7e6f62d0c12eb9f88e53a15a5daaa271ba61e68c`
- Windows Candidate run: `33296790070 = success`
- pytest: **95 passed**
- Candidate artifact: `9727721868`
- Current task: **用户本机真实 Telegram 账号 E2E，不再添加新功能**
- Release gate: 不 merge PR #20、不创建/覆盖 `v0.3.0` Release，直到真人 E2E PASS + 用户明确发布授权

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

正式线 v0.1.10 不受 Candidate 分支影响。

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

每个群必须在**该群真正开始执行导出时**单独冻结：

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

## Pre-Human-E2E Tail Audit / Fixes Completed

此前尾部审计以及 Issue #22 修复已完成：

1. Release workflow 恢复 standalone + portable `SESSION_BUSY JSON/native exit=8` gate；
2. v0.1.10 UTF-8/cp1252 regression 完整前移；
3. migrated global advanced-search legacy cursor duplicate/gap bug 已修；
4. single-chat migrated cursor / `CURSOR_STALE` 已加固；
5. legacy history role 使用 current logical Supergroup；
6. migrated rich-get logical/source IDs 一致；
7. Candidate gate 包含 one-file + portable；
8. `main@v0.1.10` 已纳入 PR #20 ancestry，PR base=`main`；
9. Issue #22：current-unread 改为 per-group export-start snapshot，并补回归；
10. migrated legacy peer 不会污染 current-unread snapshot。

## Frozen Human-E2E Candidate

**真人验收现在只使用这一版，不再使用旧 `0ad4219...` Candidate。**

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

其后的 docs-only commits 不改变该 frozen binary。

## Human E2E Pending

用户本机至少验证：

1. all dialogs：group/supergroup/channel/private/bot/Saved/archive；
2. Telegram Chat Folder membership；
3. 真实聊天最近 500 history；
4. owner/admin；
5. sender-id / current sender-role / real domain search；
6. anonymous admin/send-as 不误归属；
7. history/search 多页无 overlap/gap；
8. since/until；
9. Saved Messages history/search；
10. `MESSAGE_NOT_FOUND`；
11. `AMBIGUOUS_CHAT`；
12. v0.3 GUI + tgctl coexist；
13. legacy direct Session lock → packaged `SESSION_BUSY` + native exit 8；
14. logs/stdout safety；
15. Forum（账号有条件时）；
16. media metadata-only 不产生文件；
17. media plan 第一次不创建目录/不下载；
18. **Issue #22 real scenario**：current-unread 在每个群开始时取新 snapshot，开始后到达的新消息留到下一次；
19. media confirm / Option B read-ack 仅在用户明确选择安全目标时做副作用测试。

默认不需要重复 send/forward 真人写入；v0.1.9 已在 Saved Messages 验证过真实 write。若 v0.3 要复验，必须先 dry-run + 用户确认。

## Known Risks / Technical Debt

- CI/mock 无法代替真实 Telegram E2E；
- `capture_current_unread_snapshot()` 当前通过 `iter_dialogs()` 精确查 current chat，正确性优先；大量 dialogs + 大批群时可能有 O(groups × dialogs) 延迟，可在 E2E 后评估 targeted API 优化，不应在候选冻结前过度重构；
- branch protection 当前不是仓库强制，因此 Agent 必须自行遵守 PR/no-force-push/no-release-overwrite；
- Telegram 权限/历史可见性会因真实账号而异，unavailable 不得伪造。

## Next Steps

```text
用户下载 artifact 9727721868
→ Windows + 真实 Telegram 账号 E2E
→ 若发现问题：只修真实问题 + regression + 新 Candidate
→ E2E PASS
→ 更新正式 v0.3.0 Release Notes
→ 用户明确授权“发布 v0.3.0”
→ merge PR #20 / release workflow
→ 验证 tag/target/assets/SHA/workflow
```

在真人 E2E 结论出来前：**不继续堆新功能、不 merge PR #20、不 Release。**

# New Chat Resume Instructions

新的 GPT 接手时：

1. 读 `AGENTS.md`；
2. 读本 `HANDOFF.md`；
3. 读 `docs/PERSONAL_ACCOUNT_READER_V3_DESIGN.md`、`docs/ARCHITECTURE.md`、`docs/DECISIONS.md`、`docs/TESTING.md`、`SECURITY.md`、`docs/releases/v0.3.0.md`；
4. 查看 PR #20 当前 head / Draft 状态；
5. 查看 Issue #22 是否已按本快照关闭；
6. 核对 Latest Release 仍是 v0.1.10，除非 GitHub 已有更新事实；
7. 核对 frozen runtime run `33296790070`/artifact `9727721868`；
8. 在这些核对完成前不要修改代码。

恢复后先输出：当前 Production、Candidate、真人 E2E 状态、风险、推荐下一步。GitHub 当前事实若与本文件冲突，以 GitHub 为准并更新 HANDOFF。
