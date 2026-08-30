# HANDOFF.md

> 当前项目交接快照。新 Agent 接手时先读 `AGENTS.md`，再读本文件；恢复检查完成前不要修改代码。

# Current Project State

**Last updated:** 2026-08-30  
**Repository:** `3ll3-3ll3/tg-exporter`  
**Default branch:** `main`  
**Production version:** **v0.3.0**  
**Production commit/tag:** `8e230e33ea928bcf71296e4e5379b097446dbec5` / `v0.3.0`  
**Release workflow:** `33299040904` — `Release TG Exporter` — success  
**Release PR:** #23 `release: v0.3.0` — merged  
**Implementation history PR:** #20 — superseded by merged release PR #23  
**Issue #22:** closed/completed  
**Active correctness blocker:** none known at release time  
**Recommended next task:** post-release stabilization only; do not invent new scope until the user selects the next feature/issue.

## Production Release

GitHub Release: `https://github.com/3ll3-3ll3/tg-exporter/releases/tag/v0.3.0`

Formal assets rebuilt from final main commit:

```text
TGExporter-v0.3.0-windows-x64.exe
sha256 27c5c41f1a3e752439075cba19d1cdb5ba4aff12d5730944b03ed1c15f3252b7

TGExporter-v0.3.0-windows-x64-portable.zip
sha256 fae320914a2b75b8a993bbf313008a131846c323e915b32fa0f7af04c54a45b2

tgctl.exe
sha256 1bcc241b7b05260eb57cb42010ce156176606d88c162e87795d4d3e5229eff43

SHA256SUMS.txt
asset digest sha256 81d786363cb1a95a7a760bf06a282083e5632d701dca62e03ee5124df9148db4
```

Tag `v0.3.0` resolves directly to commit `8e230e33ea928bcf71296e4e5379b097446dbec5`.

## Project Summary

TG Exporter / TG 导出器是 Windows 本地 Telegram 工具：

- GUI：多群独立文字/caption JSON 导出；
- `tgctl`：Codex/CLI 确定性 Telegram 查询接口 + 有界 true-forward/plain-text send；
- single daemon：唯一 Telegram Session owner，GUI/tgctl 通过 authenticated Windows Named Pipe JSON IPC；
- Personal Account Reader：账号/dialog/member/rich-message/Forum/Saved Messages/media metadata 分页读取；
- 显式媒体下载：两阶段确认、本地硬上限、atomic rename。

它不是云服务、数据库、Bot API 产品、Telegram Desktop 替代品或 24/7 自主 Agent。

## Production Definition

没有远程生产数据库/服务器。Production 指：

1. GitHub 正式 Release Windows binaries；
2. 用户本机 `%APPDATA%\TelegramMultiChatExporter\` 下 Session/API/settings/checkpoint/log/cache；
3. 用户真实 Telegram 账号；
4. 用户本地导出目录。

不要删除/迁移兼容 AppData 路径，不要复制 Session 或绕过 SessionLease。

## Current Architecture

```text
TGExporter GUI ─┐
               ├→ authenticated Named Pipe / UTF-8 JSON → TG daemon → Telethon → one Telegram user Session
tgctl / Codex ─┘
```

调度：

```text
local status/job/heartbeat        immediate
export                            exclusive Telegram job
reader during export              waits
real send/forward during export   EXPORT_IN_PROGRESS, never queued
```

GUI 关闭/崩溃时 daemon-side export 可继续；daemon 有托盘，空闲约 10 分钟退出。phone/OTP/2FA 仍只在 GUI。

## Core Product Invariants

- `output_root / Export Category / group / YYYY-MM-DD_HH-mm-ss.json`；同秒 `_2/_3/...`；
- JSON 独立，不累计归档、不覆盖历史；
- Export Category 是本地分类，不是 Telegram Chat Folder；
- GUI message export text/caption only，头像只是 UI cache；
- Basic Group→Supergroup 只显示 current logical group，legacy 只用于历史；
- qasync 禁止 nested blocking modal；
- compatibility path 永久保持 `%APPDATA%\TelegramMultiChatExporter\`。

### Current unread

Issue #22 已修复：每个群在该群实际开始 current-unread 导出时冻结：

```text
lower = read_inbox_max_id_at_group_start
upper = latest_message_id_at_group_start
export only lower < id <= upper
```

snapshot 后新消息留到下一次；optional read-ack 只使用同一个 frozen upper；顺序严格 `JSON atomic success → checkpoint → optional read ack`；迁移群 current-unread 只使用 current logical Supergroup。

## v0.3 Reader

正式支持：

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

Reader：default page 100/max500、HMAC/query-bound cursor、Rich MessageInfoV3、current role snapshot、anonymous/send-as safety、current→legacy migration、real hostname domain filter、Forum、bounded JSONL、media metadata-only by default。

旧 `status/chats list/messages search/messages get/forward/send` 继续兼容。

## Write / Media Safety

- true forward；plain-text send；dry-run；forward 20/200 cap；AMBIGUOUS_CHAT；FloodWait structured stop；unknown outcome no retry；
- export 活跃时 real writes 立即拒绝；
- media download 必须 plan→confirmation→download；normal 20 files/500 MiB，large 最大 200 files/5 GiB；`.part`→atomic rename；
- 普通日志不记录 credential/Session/access_hash/file_reference/message body/caption/URL text/media filename。

## Release Validation

发布前 frozen Candidate：

```text
runtime: 7e6f62d0c12eb9f88e53a15a5daaa271ba61e68c
PR CI: 33296790070 = success
pytest: 95 passed
candidate artifact: 9727721868
```

用户于 2026-08-30 明确宣布第三版验收通过并要求继续发布。正式 Release 又从 final main commit 重新跑了 Release workflow `33299040904`，完成 pytest/import/one-file/portable/tgctl/standalone+portable SESSION_BUSY=8/smoke/assets/Release，并 success。

## Resolved Important Bugs / Regression Knowledge

- qasync nested modal task re-entry：禁止重新引入 blocking modal；
- Windows non-UTF-8 packaged tgctl 中文 JSON导致 exit1：v0.1.10 修复，v0.3 保留 source+packaged regression；
- migrated global search legacy cursor repeat/gap：已修；
- migrated rich-get logical/source ID mismatch：已修；
- current-unread catalogue-refresh snapshot stale：Issue #22 已修为 per-group export-start snapshot。

## Known Risks / Technical Debt

- `capture_current_unread_snapshot()` 当前为正确性优先，可能通过 dialogs 扫描查目标；大量 dialogs × 多群时存在性能优化空间，但不是 correctness blocker；
- Telegram 无法证明历史管理员任期、隐藏匿名身份或“查不到=已删除”；必须返回 current/unknown/unavailable 而不是猜；
- media download 是显式本地磁盘副作用；
- MCP、长期监听、自动转发规则仍未实现，除非用户开启下一阶段，不应自动扩大 scope；
- GitHub branch protection 若未强制，Agent 仍必须自行遵守 PR/no-force/no-release-overwrite。

## Current PR / Issue Cleanup

- PR #23：merged，正式 release vehicle；
- PR #20：实现历史，应关闭为 superseded by #23，不再继续开发；
- PR #21：旧 handoff docs PR 已与 v0.3 main 冲突，应由本 post-release handoff PR 取代并关闭；
- PR #17/#19：历史设计参考，不是当前实现入口；
- Issue #22：closed/completed。

## Next Steps

没有已知的 v0.3.0 发布 blocker。下一步按优先级：

1. 完成本 post-release handoff 文档 PR 并把默认 main 的恢复入口更新到 v0.3.0 Production；
2. 关闭已被替代的 #20/#21，保留历史链接；
3. 如用户报告 v0.3.0 runtime bug，建立 Issue → fix branch → PR → Windows CI → patch Release；
4. 如用户要继续产品演进，再单独确定下一阶段（例如 MCP/更高层自动化），不要在无明确需求时自行扩张。

# New Chat Resume Instructions

新 GPT 接手：

1. 读 `AGENTS.md`；
2. 读 `HANDOFF.md`；
3. 读 `README.md`、`docs/KNOWN_ISSUES.md`、`docs/ARCHITECTURE.md`、`docs/SECURITY_MODEL.md`、`docs/TESTING.md`、`docs/DEPLOYMENT.md`、`docs/RELEASE_PROCESS.md`；
4. 读与当前任务有关的 `docs/decisions/`；
5. 核对 GitHub main、Latest Release、open Issues/PRs 和最新 CI；
6. 在确认恢复正确前不要修改代码。

恢复后先向用户报告：正式版本/commit、当前架构、已知 bug/risk、open work 和推荐下一步。GitHub 当前事实优先。
