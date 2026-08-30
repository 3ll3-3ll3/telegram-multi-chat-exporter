# ADR-007 — Current-Unread Snapshot Is Frozen at Each Group's Export Start

## Status

Accepted and implemented on v0.3 Candidate branch. Issue #22 closed completed on 2026-08-30.

Validated Candidate:

```text
runtime: 7e6f62d0c12eb9f88e53a15a5daaa271ba61e68c
Windows run: 33296790070 = success
pytest: 95 passed
artifact: 9727721868
```

## Context

“Current unread” needs deterministic lower/upper bounds so messages arriving during export are neither accidentally included nor acknowledged. The earlier implementation froze those bounds when the group catalogue was loaded/refreshed, which could be minutes before a later group in a batch actually started exporting.

## Decision

For every group using current-unread mode, capture a fresh immutable snapshot **when that group's export begins**:

```text
lower = read_inbox_max_id_at_group_start
upper = latest_message_id_at_group_start

export only:
lower < message_id <= upper
```

Optional “mark read after export” may acknowledge only through that exact same frozen `upper`, and only after:

```text
JSON atomic success
→ checkpoint success
→ optional read acknowledgement
```

Messages arriving after the snapshot remain outside this run and are not acknowledged by it.

Each group in a multi-group batch gets its own snapshot when that group begins; there is no catalogue-global or batch-global unread snapshot.

Basic Group→Supergroup current-unread uses only the current logical Supergroup. The legacy Basic Group remains a historical source for appropriate history/date-range behavior, not current unread.

## Implementation

v0.3 daemon now refreshes safe read/latest state immediately before each unread group execution, copies it into that group's execution plan, and passes the same frozen `GroupInfo` copy to both `export_group()` and optional `mark_unread_snapshot_read()`.

The catalogue/workspace object is not mutated.

## Why

This matches “export the unread messages that are current when this group starts exporting” while preserving deterministic behavior during the run.

## Alternatives Considered

### Freeze at catalogue refresh

Rejected: stale if the user waits before export or if earlier groups take time.

### No upper bound / read until live end

Rejected: messages arriving mid-export make the set non-deterministic and can be unintentionally acknowledged.

### One batch-global snapshot

Rejected: later groups can start much later; each group must freeze independently.

## Consequences

The daemon performs a fresh read-state lookup per current-unread group at execution start. This is correctness-first and may add catalogue-scan cost for accounts with many dialogs; optimize only if real E2E shows meaningful latency, without changing the semantics.

## Risks

Telegram read acknowledgement advances a read pointer. Media/service items inside the frozen ID range that are not written to the text-only JSON may still become read. The GUI warning and default-OFF read-ack policy remain necessary.
