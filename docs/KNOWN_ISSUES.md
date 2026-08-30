# Known Issues

本文件记录当前阻塞项与已经解决但需要长期回归保护的问题。GitHub 当前事实优先于本文。

## Current status

截至 2026-08-30：

- Production：`v0.3.0 @ 8e230e33...`；
- v0.3.1：PR #24 Draft Candidate；
- **没有已知未修复的自动化 correctness blocker**；
- v0.3.1 GitHub/CI/package gate 已通过，剩余风险来自用户本机 Windows `%APPDATA%` / 真实 Telegram 账号的人类验收，不能由 CI 代替。

仍需真人/本机验证的类别包括：真实 packaged domain+regex 查询、GUI 多场景关闭、两个 GUI 顺序关闭后 daemon/tgctl 可用、真实新日志段异常计数、同一 bounded sender 样本修复后聚合统计。

## KI-001 — Current-unread snapshot captured too early

**Status: RESOLVED / released in v0.3.0.**  
GitHub Issue #22 已 closed completed。

正确语义：

```text
lower = read_inbox_max_id_at_group_start
upper = latest_message_id_at_group_start
export only lower < message_id <= upper
```

每群在自身 execution start 单独 snapshot；post-snapshot 新消息不进入本轮；export/read-ack 复用同一 upper；export failure 不 ack；JSON success + ack failure 保留 JSON；migrated current-unread 只看 current logical Supergroup。

长期回归见 ADR-007 与 `tests/test_unread_snapshot_export_start.py`。

## KI-002 — Packaged `--url-domain` normalization crash

**Status: RESOLVED on v0.3.1 Candidate.**

原因：冻结的 `tgctl.exe` 可能缺失动态 `idna` codec lookup。修复为显式离线 stdlib IDNA normalization + PyInstaller hidden import + final standalone/portable packaged search-filter smoke。非法域名返回 `INVALID_ARGUMENT`，不退化成 `TELEGRAM_ERROR`。

## KI-003 — GUI normal close could stop qasync loop too early

**Status: RESOLVED on v0.3.1 Candidate; local Windows close scenarios still require human verification.**

修复：last-window-close 触发 cleanup；先 cancel/await init/job-monitor/heartbeat + detach GUI lease，再让 async app 返回；shared daemon 不被 GUI close 终止；不使用 `loop.stop()` 隐藏问题。

## KI-004 — Sender/owner diagnostics too coarse + acceptance regex gap

**Status: RESOLVED in automated v0.3.1 Candidate; real bounded sender sample still requires human before/after measurement.**

- sender 使用 Telegram peer fields，不从正文/昵称猜；
- actual sender 与 forward_origin 分开；
- unresolved 保持 unknown + unknown_reason；
- owner visibility 区分 permissions/unavailable/pagination/not-returned；
- v0.3.0 缺失的 `--regex` 已作为 bounded local filter 补齐，并纳入 cursor binding 与 packaged smoke。

## Historical regression knowledge

后续修改相邻代码时保留这些长期 gate：

- qasync nested blocking modal 曾导致 task re-entry；
- Windows cp1252/UTF-8 曾把 packaged `SESSION_BUSY` native exit 8 破坏成 exit 1；
- migrated global advanced-search legacy cursor 曾出现 duplicate/gap；
- migrated rich-get logical/source chat identity 曾不一致；
- zero-current-unread 必须输出合法 empty JSON，不能因为 `min_id=0` 扫全历史；
- proxy safe label 不得包含用户名、密码或 query。

最终 Candidate run/artifact/hash 以 PR #24 body 与最新 CI 为准，避免复制旧候选数字造成状态漂移。