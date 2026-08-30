# Architecture Decision Records

这里存放会长期影响实现、安全或产品语义的关键 ADR。

历史较细的 `D-xxx` 决策摘要仍保留在 [`../DECISIONS.md`](../DECISIONS.md)；本目录用于保存最重要决定的 Context / Why / Alternatives / Consequences，避免后续 Agent 重走已经否决的方案。

| ADR | Status | Summary |
| --- | --- | --- |
| [ADR-001](001-single-daemon-session-owner.md) | Accepted | v0.2+ single daemon 是唯一 Telegram Session owner |
| [ADR-002](002-local-named-pipe-json-ipc.md) | Accepted | Windows Named Pipe + authenticated UTF-8 JSON bytes；拒绝 TCP/HTTP/pickle |
| [ADR-003](003-bounded-reader-pagination-and-safe-cursors.md) | Accepted | Reader default 100/max500；HMAC/query-bound safe cursor |
| [ADR-004](004-telegram-write-safety-and-no-auto-retry.md) | Accepted | Telegram write 显式/有上限；unknown outcome 不自动 replay |
| [ADR-005](005-migrated-group-logical-identity.md) | Accepted | Current Supergroup 是 logical chat；legacy Basic Group 仅 historical source |
| [ADR-006](006-human-e2e-release-gate.md) | Accepted | v0.3 必须真人 E2E + 用户明确授权后才能 merge/release |
| [ADR-007](007-current-unread-snapshot-at-export-start.md) | Accepted requirement / runtime pending | Current-unread 每个群在**该群开始导出时**冻结；当前 KI-001 尚未实现 |

## When to add an ADR

建立/更新 ADR，当且仅当决定：

- 会长期影响架构/安全/数据语义；
- 存在多个合理方案且已经明确选定；
- 后续 Agent 很可能重新提出已否决方案；
- 改变后会需要迁移、重新 E2E 或安全评估。

不要用 ADR 记录普通每日进度、小 bug 或聊天过程。

## Changing an accepted decision

用户明确改变方向时：

1. 新建 ADR 或在原 ADR 标记 Superseded；
2. 写清新 Context/Decision/Consequences；
3. 更新 `docs/DECISIONS.md` 索引；
4. 更新 `HANDOFF.md` Current State / Recent Decisions / Risks；
5. 若涉及 Production/security，同时更新 `docs/SECURITY_MODEL.md`；
6. runtime 改动重新按 `docs/TESTING.md` 验证。