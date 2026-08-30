# ADR-007 — Current-Unread Snapshot Is Frozen at Each Group's Export Start

## Status

Accepted product requirement. **Current runtime does not yet conform; see `docs/KNOWN_ISSUES.md` KI-001.**

## Context

“Current unread” must have a deterministic upper/lower bound so messages arriving during export are not accidentally included/acknowledged. Earlier implementation froze those bounds when the group catalogue was loaded/refreshed, which can be minutes before a later group in a batch actually starts exporting.

## Decision

For every group using current-unread mode, capture a fresh immutable snapshot **when that group's export begins**:

```text
lower = read_inbox_max_id_at_export_start
upper = latest_message_id_at_export_start

export only:
lower < message_id <= upper
```

Optional “mark read after export” may acknowledge only through that same frozen `upper`, and only after:

```text
JSON atomic success
→ checkpoint success
→ optional read acknowledgement
```

Messages arriving after the snapshot remain outside this run and must not be acknowledged by it.

Each group in a multi-group batch gets its own snapshot when that group begins; there is no catalogue-global or batch-global unread snapshot.

Basic Group→Supergroup current-unread uses the current logical Supergroup only.

## Why

This matches what a user reasonably means by “export the unread messages that are current when you start exporting this group,” while preserving deterministic behavior during the export itself.

## Alternatives Considered

### Freeze at catalogue refresh

Rejected as product semantics: stale if the user waits before export or if earlier groups take time.

### No upper bound / read until live end

Rejected: messages arriving mid-export make the set non-deterministic and can be unintentionally marked read.

### One batch-global snapshot

Rejected: later groups can start much later; each group should freeze at its own execution start.

## Consequences

The daemon/export path must refresh safe dialog/read state immediately before each unread group export and pass the frozen snapshot through both export and optional acknowledgement.

## Risks

Telegram read acknowledgement advances a read pointer. Media/service items within the frozen ID range that are not written to the text-only JSON can still become read. The GUI warning/default-OFF policy remains necessary.