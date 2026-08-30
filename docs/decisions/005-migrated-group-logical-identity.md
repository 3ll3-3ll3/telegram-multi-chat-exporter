# ADR-005 — Basic Group Migration Uses One Logical Current Chat

## Status

Accepted since v0.1.8; extended by v0.3 reader.

## Context

Telegram can migrate a legacy Basic Group (`Chat`) into a Supergroup (`Channel` with megagroup semantics). Telethon may expose both peers. Showing both creates duplicate-looking groups, while dropping the legacy peer entirely loses pre-migration history.

## Decision

Treat the current Supergroup as the user-visible **logical chat** and the old Basic Group as a historical source only.

Rules:

- catalogue/dialog selection shows one logical current chat;
- migration relation must come from Telegram metadata, never same-name guessing;
- do not delete/leave/downgrade/modify the real Supergroup;
- current-unread and since-last operate on the current Supergroup;
- date-range/history may traverse current then legacy history;
- message identity across migration is `(source_chat_id, message_id)`;
- rich output from legacy history keeps:

```text
chat_id        = current logical Supergroup
source_chat_id = legacy Basic Group
message_id     = source message id
```

- owner/admin/member role snapshot is based on the current logical group, because historical role tenure is not reliably available.

## Why

This matches how users perceive the chat while preserving old messages without inventing identity relationships.

## Alternatives Considered

### `ignore_migrated=True` and forget legacy history

Rejected as a complete solution: it fixes catalogue duplication but can silently omit pre-migration history.

### Show old and new peers as separate groups

Rejected: confusing UX and duplicate logical membership/settings.

### Merge by same title

Rejected: unrelated Telegram chats can share a title.

### Deduplicate only by message id

Rejected: message ids are peer-local and can collide across legacy/current sources.

## Consequences

Pagination/search cursors need a current/legacy segment. Settings/categories/workspace should follow the current logical peer where possible.

## Risks

Telegram migration metadata can be unavailable/stale. In that case return explicit stale/unavailable semantics rather than guessing.