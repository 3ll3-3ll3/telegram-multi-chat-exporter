# HANDOFF.md

> 当前项目交接快照。新 Agent / GPT 接手时先读 `AGENTS.md`，再读本文件；恢复检查完成前不要修改代码。

# Current Project State

**Last updated:** 2026-08-30 14:35 +08:00  
**Repository:** `3ll3-3ll3/tg-exporter`  
**Default branch:** `main`  
**Production version:** `v0.1.10`  
**Production commit/tag:** `cedb02035597aa607fac399666154519f480c431` / `v0.1.10`  
**Current development version:** `v0.3.0` Candidate  
**Current development branch:** `codex/personal-account-reader-v0.3.0`  
**Implementation PR:** Draft PR #20 `feat: v0.3.0 personal account reader candidate`  
**Handoff docs PR:** PR #21 `docs: persist project context for AI handoff`  
**Issue #22 / KI-001:** **CLOSED / fixed**  
**Frozen human-E2E runtime Candidate:** `7e6f62d0c12eb9f88e53a15a5daaa271ba61e68c`  
**Windows Candidate run:** `33296790070 = success`  
**pytest:** `95 passed`  
**Artifact:** `9727721868`  
**Current task:** 用户本机真实 Telegram 账号 v0.3 E2E；测试前不再加功能  
**Release gate:** PR #20 不 merge；不创建/覆盖 `v0.3.0` Release，直到真人 E2E PASS + 用户明确发布授权

## Source-of-truth warning

`main` 是正式 Production 线，不是最新 runtime。v0.3 daemon/reader 实现在 PR #20。

历史 Draft PR #17（daemon design）和 #19（reader design）已经被 #20 吸收，仅是设计依据，不是继续实现入口。

# Project Summary

TG Exporter / TG 导出器是 Windows 本地 Telegram 工具：

- GUI：多群独立 text/caption JSON 导出；
- `tgctl`：供 Codex/CLI 读取、搜索，以及在安全边界内 true-forward / pure-text send；
- v0.2/v0.3：single daemon 唯一拥有 Telegram Session，GUI/tgctl 走本地 IPC；
- v0.3 Personal Account Reader：分页读取账号、dialogs、成员/管理员、rich messages、Forum、Saved Messages、media metadata，并提供显式两阶段本地媒体下载。

它不是 Telegram Desktop 替代品、累计数据库、云服务、Bot API 应用或 24/7 自主 Agent。

# Production Definition

本项目没有远程 Production DB/server/cloud runtime。Production 指：

1. GitHub 正式 Release Windows 二进制；
2. 用户本机 `%APPDATA%\TelegramMultiChatExporter\` Session/config/state/log/cache；
3. 用户真实 Telegram 账号；
4. 用户选择的本地导出目录。

# Production Version

Latest formal Release：**v0.1.10**，target `cedb02035597aa607fac399666154519f480c431`。

```text
TGExporter-v0.1.10-windows-x64.exe
sha256 b598aecdd7fcc3f5731ba955f7f02d8bd45ea47220f66a040bc20b64f4e410be

TGExporter-v0.1.10-windows-x64-portable.zip
sha256 113c6f8223d6f648571bf8ad3e86a1df1db2ad1e118bb2674e70f0031b0274dd

tgctl.exe
sha256 ebd6cd8898f51aa9e63a7efa6292a70df0afe15cd5efe99b7fc4be9bbf2f5efa
```

v0.1.10 修复 packaged Windows 非 UTF-8 console 下中文 JSON error 导致 `SESSION_BUSY` native exit 8 退化为 exit 1 的问题；该修复与 regression 已 forward-port 到 v0.3。

# Current Architecture

## Production v0.1.10

```text
GUI ─┐
     ├→ direct TelegramService/Telethon → one SQLiteSession
 tgctl┘
```

OS `SessionLease` 防止并发 direct ownership。不得绕过/复制 Session。

## Candidate v0.3

```text
GUI ─┐
     ├→ authenticated Windows Named Pipe + UTF-8 JSON → TG daemon → TelegramService/Telethon → one Session
 tgctl┘
```

Daemon 是唯一 Session owner。同代 GUI + tgctl 正常共存；`SESSION_BUSY` 只用于 legacy/direct process 已持有 SessionLease 的兼容边界。

```text
LOCAL status/job/heartbeat       → immediate
export                           → exclusive Telegram job
reader                           → waits during export
real send/forward during export  → EXPORT_IN_PROGRESS, never queued
```

# Core Product Invariants

- 输出 `root / Export Category / group / YYYY-MM-DD_HH-mm-ss.json`；同秒 `_2/_3/...`；
- Export Category 是软件本地分类，不是 Telegram Chat Folder；删除分类不删除历史文件；
- 每个 JSON 独立，不读/合并/覆盖历史导出；
- GUI 消息导出 text/caption only；头像仅 UI cache；
- Basic Group→Supergroup 只显示 current logical group；legacy peer 只作历史来源；
- qasync 不重新引入 nested blocking modal；
- AppData 兼容路径固定 `%APPDATA%\TelegramMultiChatExporter\`；
- mark-read 默认 OFF；`JSON atomic success → checkpoint → optional read ack`。

## Current-unread fixed semantics

Issue #22 已修复。每个群在**该群真正开始执行导出时**单独冻结：

```text
lower = read_inbox_max_id_at_group_start
upper = latest_message_id_at_group_start
export only lower < id <= upper
```

- 不再使用 catalogue refresh 时的旧边界；
- 多群 batch 每群轮到执行时分别刷新；
- snapshot 后到达的消息不进入本次 run；
- export 与 optional read-ack 使用同一个 frozen upper；
- export failure 不 read-ack；read-ack failure 不删除成功 JSON；
- migrated current-unread 只使用 current logical Supergroup，legacy Basic Group 不参与。

Issue：<https://github.com/3ll3-3ll3/tg-exporter/issues/22>（closed completed）  
ADR：`docs/decisions/007-current-unread-snapshot-at-export-start.md`

# Completed

## Stable v0.1.x

Windows GUI export、focused workspace、Telegram Folder filter、avatar lazy load、Export Categories、migration catalogue/history、current-unread/since-last/Option-B、Windows proxy、qasync fixes、tgctl status/chats/search/get/forward/send、JSON/error contract、dry-run/20-200 cap/ambiguity/FloodWait、v0.1.9 real Saved Messages send/forward E2E、v0.1.10 UTF-8/exit-code hotfix。

## v0.2 inherited by v0.3

`codex/single-daemon-v0.2.0 @ 165b0a86c85049cb25ab51f601c210ef986556a2`：single daemon、Named Pipe IPC、GUI/tgctl clients、tray、lease/heartbeat、daemon-side export、coordinator、idle shutdown、write scheduling。未单独正式 Release；v0.3 继承。

## v0.3 Candidate

PR #20 已实现：

```text
tgctl account get
tgctl dialogs list
tgctl chats get/chats members
tgctl messages history/search/get
tgctl topics list/history
tgctl media download
```

以及 bounded pagination、HMAC/query-bound cursor、Rich MessageInfoV3、current role snapshot、anonymous/send-as safety、current→legacy migration history、hostname domain filter、Forum、metadata-only media + confirmed bounded download。

发布前还已修复：standalone+portable packaged `SESSION_BUSY=8` gate、cp1252/UTF-8 regression、migrated global search cursor、single-chat migrated cursor stale semantics、migration role/current entity、rich-get logical/source IDs、one-file+portable Candidate gate、main ancestry 整合，以及 Issue #22 per-group export-start unread snapshot。

# Frozen Human-E2E Candidate

旧 `0ad4219... / run 33293667296 / artifact 9726786295` 仅作历史追溯，不再用于最终真人验收。

当前真人验收固定使用：

```text
runtime head: 7e6f62d0c12eb9f88e53a15a5daaa271ba61e68c
Windows run: 33296790070 = success
pytest: 95 passed in 2.19s
artifact id: 9727721868
artifact name: TGExporter-v0.3.0-candidate-windows-x64
artifact URL: https://github.com/3ll3-3ll3/tg-exporter/actions/runs/33296790070/artifacts/9727721868
```

```text
TGExporter-v0.3.0-candidate-windows-x64.exe
sha256 0afccfe03c005b78ad90aefd904f75fa53f536f22f7d90a90f00f1928fd403ae

TGExporter-v0.3.0-candidate-windows-x64-portable.zip
sha256 5fae791e3e8a87bafcfc4b17256349d1945787b163d4114a01bed05fadb9f7e8

tgctl.exe
sha256 01e566de4cc95fff273b68e4039b346843e2b3c54ee8f4afb74e9fe7a50189d5

outer Actions artifact ZIP
sha256 f68ea1d7b711f51c122a972008a32f1ffa06355ba1c85bdc9bd870e4fb67caca
```

Candidate gate 已通过 pytest、GUI+daemon+reader+CLI imports、one-file/portable builds、standalone/portable `SESSION_BUSY JSON/native exit 8`、全部 packaged smoke、SHA generation、artifact upload。

其后的 docs-only commits 不替换上述 runtime binary。

# In Progress

**唯一当前产品任务：用户真人 Telegram 账号 E2E。**

在 E2E 结论前：不继续堆新功能、不 merge PR #20、不创建 v0.3.0 Release。

# Human E2E Pending

至少覆盖：

- all dialog types + Telegram Folder；
- real 500 history；
- owner/admin、sender/current-role/domain filters；
- anonymous/send-as identity safety；
- multi-page history/search no overlap/gap；
- since/until；
- Saved Messages；
- MESSAGE_NOT_FOUND / AMBIGUOUS_CHAT；
- v0.3 GUI + tgctl coexist；
- legacy direct lock → SESSION_BUSY + native exit 8；
- log/stdout safety；
- Forum if available；
- media metadata-only no files；
- media plan no directory/files；
- **current-unread real scenario**：每群执行开始时重新冻结，之后到达的消息留到下一次。

Default E2E 不需要重复真实 send/forward。media confirm 或 Option-B read-ack 只在用户明确选择安全目标时测试。

# Known Bugs

截至本快照，没有已知未修复的 automated-Candidate blocker。KI-001 / Issue #22 已关闭并有 regression。

历史回归知识：qasync nested modal task re-entry；packaged cp1252 Unicode error/exit1；migrated global-search legacy cursor repeat/gap；migrated rich-get ID mismatch。

# Known Risks / Technical Debt

- CI/mock 不能替代真实账号 E2E；
- `capture_current_unread_snapshot()` 当前通过 `iter_dialogs()` 精确查 current chat，correctness-first；大量 dialogs × 多群可能有额外延迟，只有真人 E2E 证明需要时才优化；
- branch protection 不是 GitHub 强制；Agent 必须自觉 no-direct-main/no-force/no-release-overwrite；
- Telegram 无法证明历史管理员任期、隐藏匿名身份或 deleted status，必须 unknown/unavailable 而不是猜；
- v0.2 未单独 Release；v0.3 继承；
- MCP 仍是 future direction only。

# Important Constraints / Production Safety

不要迁移/删除兼容 AppData；不要删历史 JSON；不要复制/绕过 SessionLease；不要按同名猜 migration；不要反推匿名身份；不要把 unavailable 说成 deleted；reader 不得隐式 write/read-ack；Actions Artifact 不是 Production Release；不得把真实 Telegram Secret 放 Actions；真实 Telegram write/media side effect 必须明确授权。

# Next Steps

1. 用户下载 artifact `9727721868`；
2. Windows + 真实 Telegram 账号 E2E；
3. 如果发现问题，只修真实问题 + regression + 新 Candidate；
4. E2E PASS 后收尾正式 v0.3 Release Notes；
5. 用户明确授权“发布 v0.3.0”；
6. merge PR #20 / formal Release workflow；
7. 验证 tag、target、one-file、portable、tgctl、SHA、workflow；
8. 更新 Production HANDOFF。

# Recommended Next Task

**不要再写新功能。让用户开始测试 frozen Candidate `7e6f62d... / artifact 9727721868`。**

# New Chat Resume Instructions

新的 GPT 在修改代码前：

1. 阅读 `AGENTS.md`；
2. 阅读 `HANDOFF.md`；
3. 阅读 `README.md`；
4. 阅读 `docs/KNOWN_ISSUES.md`、`docs/ARCHITECTURE.md`、`docs/SECURITY_MODEL.md`、`SECURITY.md`；
5. 阅读 `docs/TESTING.md`、`docs/DEPLOYMENT.md`、`docs/RELEASE_PROCESS.md`；
6. 阅读相关 `docs/decisions/` ADR，特别 ADR-006/007；
7. 查看 PR #20、PR #21、Issue #22；
8. 核对 main、Latest Release、Candidate run/artifact；
9. 在恢复确认前不要修改代码。

恢复后先告诉用户：Production、Candidate、真人 E2E 状态、已知风险、推荐下一步。GitHub 当前事实若与本文件冲突，以 GitHub 为准并更新 HANDOFF。
