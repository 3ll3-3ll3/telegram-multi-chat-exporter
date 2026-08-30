# ADR-002 — Authenticated Windows Named Pipe with UTF-8 JSON Bytes

## Status

Accepted for v0.2+.

## Context

Once Telegram ownership moves to a daemon, GUI and `tgctl` need local IPC. The product is Windows-local and does not need a network server.

## Decision

Use Windows Named Pipe / Python `multiprocessing.connection` `AF_PIPE` with local authentication and **UTF-8 JSON bytes only**.

- use `send_bytes` / `recv_bytes`;
- do not use pickle object transport;
- do not expose TCP/HTTP/Web endpoints;
- persist a local non-public IPC identity/auth secret in AppData;
- keep messages bounded; large export bodies stay daemon-side rather than crossing IPC.

## Why

- local-only matches product scope;
- avoids firewall/network exposure;
- JSON has explicit, auditable schemas and is safer than arbitrary pickle deserialization;
- works for GUI, CLI and a future thin MCP adapter.

## Alternatives Considered

### localhost HTTP/TCP server

Rejected for current scope: adds a network listener, port lifecycle and a larger trust boundary for no user benefit.

### Pickle over `multiprocessing.connection`

Rejected: unsafe/opaque object deserialization and unnecessary coupling.

### Windows Service

Rejected: daemon is on-demand user-mode software, not a system service.

## Consequences

- IPC schemas/error codes become compatibility contracts;
- auth secret must never enter stdout/log/Git;
- clients may automatically wake the daemon;
- transport failures for Telegram writes need special treatment because the client cannot know whether Telegram accepted the write.

## Risks

A process that already controls the same Windows user/AppData may read local identity data; this design does not claim to defend against a fully compromised local user account.