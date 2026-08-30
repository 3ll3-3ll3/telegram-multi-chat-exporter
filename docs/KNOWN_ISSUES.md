# Known Issues

本文件只记录**当前仍未解决、会影响后续开发/验收的已知问题**。已完全解决且仅有历史意义的 bug 放在 `HANDOFF.md` 的历史回归知识中。

## KI-001 — Current-unread snapshot is captured too early

**Status:** Open / correctness mismatch / should be fixed before final v0.3 human E2E sign-off.  
**Affected:** Production v0.1.x behavior and inherited v0.3 export path unless changed.  
**Discovered during AI handoff audit:** 2026-08-30.

### Intended product semantics

For each group using **current unread**, freeze the unread window at the moment that group's export actually begins:

```text
start_read_inbox_max_id < message_id <= latest_message_id_at_export_start
```

Messages arriving after that per-group export snapshot must not be included or acknowledged by this run.

This matters especially for a batch with many groups: group 5 may begin several minutes after the GUI catalogue was last refreshed.

### Current implementation

Current code uses the `GroupInfo.read_inbox_max_id` and `GroupInfo.latest_message_id` values captured when the group catalogue was loaded/refreshed.

`src/telegram_exporter/exporter.py` currently documents/implements:

```text
Freeze "current unread" to the dialog snapshot captured when the
group catalogue was loaded/refreshed.
```

`ExportCoordinator` deserializes the submitted plan and calls `export_group()` directly; it does not refresh the per-group Telegram read/latest state immediately before exporting that group. `mark_unread_snapshot_read()` also acknowledges `plan.group.latest_message_id`, i.e. the same earlier snapshot.

### Why this is a bug

A long delay can exist between catalogue refresh and export start. During that interval:

- messages that were unread at actual export start but arrived after refresh can be omitted;
- the run's notion of “current unread” does not match the user-confirmed definition;
- in multi-group batches, later groups can have increasingly stale snapshot bounds.

The current implementation is internally consistent for acknowledgement (it does not acknowledge beyond its stale upper bound), but the snapshot timing itself is wrong.

### Required fix direction

Do **not** solve this by removing the upper bound or by reading live-unbounded history.

At the beginning of each group's current-unread export, while the daemon/export owns Telegram work:

1. fetch the current dialog/read state for that logical current chat;
2. freeze `read_inbox_max_id` and `latest_message_id` into an immutable per-export snapshot;
3. export only `read_inbox_max_id < id <= latest_message_id`;
4. after JSON atomic success + checkpoint, optional read acknowledgement may advance only through that frozen `latest_message_id`;
5. messages arriving after the snapshot remain unread/not exported by this run.

Basic Group→Supergroup current-unread continues to use only the current Supergroup.

### Regression tests required

At minimum:

- catalogue snapshot old, export-start snapshot newer → export uses newer start snapshot;
- message arrives after export-start snapshot → excluded;
- optional read ack uses exactly export-start frozen upper bound;
- export failure → no read ack;
- JSON success + read-ack failure → JSON remains;
- multi-group batch obtains a separate snapshot when each group begins, not one batch-global or catalogue-global snapshot.

### Release impact

Do not mark v0.3 human E2E fully PASS or release v0.3.0 while this mismatch is known and unfixed, unless the user explicitly changes the product requirement back to catalogue-refresh semantics.
