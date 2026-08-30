# Known Issues

本文件优先记录**当前仍未解决、会影响后续开发/验收的问题**。已解决但具有长期回归价值的问题可保留简短历史记录，并指向对应 Issue/ADR。

## Current open blockers

截至 2026-08-30，**没有已知未修复的 v0.3 automated-Candidate correctness blocker**。下一阶段未知项主要来自用户真实 Telegram 账号 E2E。

## KI-001 — Current-unread snapshot was captured too early

**Status:** Resolved on v0.3 Candidate branch / GitHub Issue #22 closed completed.  
**Fixed runtime Candidate:** `7e6f62d0c12eb9f88e53a15a5daaa271ba61e68c`  
**Windows Candidate run:** `33296790070 = success`, **95 passed**.  
**Artifact:** `9727721868`.

### Correct semantics now implemented

For each group using current-unread mode, freeze the unread window when **that specific group's export actually begins**:

```text
lower = read_inbox_max_id_at_group_start
upper = latest_message_id_at_group_start
export only lower < message_id <= upper
```

- stale catalogue values are not used as execution bounds;
- each group in a multi-group batch gets its own execution-start snapshot;
- messages arriving after the snapshot remain outside this run;
- export and optional read acknowledgement use the exact same frozen upper bound;
- export failure never acknowledges read state;
- JSON success + read-ack failure keeps the JSON;
- Basic Group→Supergroup current-unread uses only the current logical Supergroup, not the legacy peer.

Implementation lives in PR #20 branch, including `src/telegram_exporter/unread_snapshot.py` and daemon `ExportCoordinator` execution-plan freezing. Regression tests cover multi-group timing, upper-bound behavior, migrated legacy/current identity, failure/no-ack and JSON-survives-ack-failure.

Issue: <https://github.com/3ll3-3ll3/tg-exporter/issues/22>  
ADR: `docs/decisions/007-current-unread-snapshot-at-export-start.md`

## Historical regression knowledge

Keep these in mind when changing adjacent code:

- qasync blocking modal caused asyncio task re-entry; do not reintroduce nested modal loops;
- packaged Windows cp1252 Chinese JSON error handling once changed `SESSION_BUSY` native exit 8 into exit 1; standalone/portable packaged regression must remain;
- migrated global advanced-search legacy cursor once caused duplicate/gap behavior;
- migrated rich-get logical/source chat identity once diverged.
