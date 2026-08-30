# Known Issues

本文件只记录当前仍值得下一位维护者注意的问题。已解决的 correctness bug 作为 regression knowledge 保留，但不再标成 blocker。

## Open blocker

**None known at v0.3.0 release time.**

## Technical debt / caveats

### KI-TD-001 — current-unread snapshot lookup performance

`capture_current_unread_snapshot()` 当前以正确性优先获取当前 logical chat 的 read/latest state。大量 dialogs + 大批 current-unread 群时可能存在额外扫描开销。只有出现真实性能问题时才优化；不得为了性能退回 catalogue-refresh snapshot 或破坏 per-group export-start 语义。

### KI-TD-002 — Telegram information limits

Telegram API 不能可靠证明历史管理员任期、匿名管理员 behind-the-scenes user、或“当前查不到的消息一定已删除”。Reader 必须继续返回 current snapshot / unknown / unavailable / `MESSAGE_NOT_FOUND`，不得猜测。

### KI-TD-003 — future scope intentionally absent

MCP、24/7 listener、自动转发规则、AI 自动回复/管理功能尚未实现。这是范围选择，不是 v0.3.0 bug。

## Resolved regression knowledge

- Issue #22：current-unread 从 catalogue-refresh snapshot 修为 per-group export-start snapshot；
- migrated global search legacy cursor repeat/gap：已修；
- migrated rich-get logical/source ID mismatch：已修；
- qasync nested modal task re-entry：已修，禁止重新引入 blocking modal；
- v0.1.10 packaged non-UTF-8 Chinese JSON 导致 `SESSION_BUSY` exit 1：已修并保留 packaged exit=8 regression。
