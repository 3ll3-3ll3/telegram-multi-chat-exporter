# ADR-001 — Single Telegram Daemon Owns the User Session

## Status

Accepted for v0.2+ / inherited by v0.3.

## Context

v0.1.x GUI and `tgctl` both need the same Telethon SQLiteSession. Direct multi-process access risks SQLite locking and Session corruption. v0.1.x therefore uses `SessionLease`, but that prevents the desired GUI + Codex coexistence and cannot keep exports alive after GUI exit.

## Decision

Use one local daemon as the **only** `TelegramClient` / `TelegramService` / `telegram.session` owner.

```text
TG daemon
├─ GUI IPC client
├─ tgctl IPC client
└─ future MCP client
```

GUI/tgctl must not fall back to opening the Session directly.

## Why

- one Session owner eliminates normal GUI↔tgctl SQLite competition;
- export jobs can continue after GUI closes/crashes;
- Telegram operation ordering can be made predictable;
- future MCP can reuse the same core rather than create a third Session path.

## Alternatives Considered

### Keep direct GUI/tgctl + OS lock

Safe enough for v0.1.x but forces one frontend at a time and cannot provide the target daemon experience.

### Copy/create a second Session

Rejected: introduces divergent auth/session state and weakens safety.

### Always-running Windows Service

Rejected: unnecessary privilege/lifecycle complexity. The accepted daemon is user-mode, on-demand, tray-visible, and idles out.

## Consequences

- v0.3 GUI + v0.3 tgctl should normally coexist without `SESSION_BUSY`;
- legacy/direct binaries may still trigger `SESSION_BUSY` when they hold the old Session lock;
- login interaction remains GUI-only;
- daemon lifecycle/IPC become critical infrastructure.

## Risks

Daemon failure becomes a shared failure point, so job metadata, safe shutdown and clear `DAEMON_UNAVAILABLE`/`WRITE_OUTCOME_UNKNOWN` semantics are required.