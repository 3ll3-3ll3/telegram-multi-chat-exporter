# ADR-004 — Telegram Write Safety and No Automatic Retry

## Status

Accepted since v0.1.9; inherited by daemon/v0.3.

## Context

`tgctl` can act through the user's real Telegram user account. A mistaken target, ambiguous chat, duplicate retry, or delayed queued send can create irreversible user-visible side effects.

## Decision

Telegram writes remain explicit and bounded.

### Forward

- must use Telegram true forward;
- support `--dry-run`;
- default batch <= 20;
- explicit large mode hard cap <= 200;
- ambiguous chat → `AMBIGUOUS_CHAT`, never first-match.

### Send

- plain text only;
- `parse_mode=None`;
- support `--dry-run`.

### Failure semantics

- FloodWait → structured `FLOOD_WAIT` + retry delay; no retry storm;
- while export active, real send/forward → `EXPORT_IN_PROGRESS`; never queue for later silent delivery;
- after a write request has been handed to the daemon, transport disconnect before response → `WRITE_OUTCOME_UNKNOWN`; never automatically replay the request.

Logs record only safe IDs/count/result, not message bodies.

Human write E2E uses dry-run first and prefers Saved Messages.

## Why

The cost of a duplicate or misdirected Telegram write is higher than the inconvenience of asking the user to retry manually after checking the target chat.

## Alternatives Considered

### Automatically retry all transient failures

Rejected: a request may already have reached Telegram; replay can duplicate sends/forwards.

### Queue writes until export finishes

Rejected: the user explicitly chose rejection over surprising future delivery.

### Resolve ambiguous names by first match

Rejected: unsafe for user accounts with same-name dialogs.

### Remove caps for Codex convenience

Rejected: a single mistaken natural-language instruction could create a large side effect.

## Consequences

Automation must handle structured errors and may require explicit user confirmation/retry. Read-only commands can be more permissive, but write safety may not be weakened just because a future MCP adapter is added.

## Risks

`WRITE_OUTCOME_UNKNOWN` requires the user/agent to inspect the destination before retrying. This is intentional.