# Architecture Decision Records

独立 ADR 保存长期影响较大的“为什么这样设计”。历史细粒度决策仍可在 `docs/DECISIONS.md` 查询。

当前核心 ADR：

1. `001-single-daemon-session-owner.md`
2. `002-local-named-pipe-json-ipc.md`
3. `003-bounded-reader-pagination-and-safe-cursors.md`
4. `004-telegram-write-safety-and-no-auto-retry.md`
5. `005-migrated-group-logical-identity.md`
6. `006-human-e2e-release-gate.md`
7. `007-current-unread-snapshot-at-export-start.md`

除非用户明确改变方向，否则 Accepted ADR 不应被下一位 Agent 随意反转。改变 Accepted 决策时，新建/更新 ADR 并同步 HANDOFF。
