# ADR-003 — Bounded Reader Pagination and HMAC-Bound Safe Cursors

## Status

Accepted for v0.3.

## Context

Codex needs account-wide dialogs/history/search, but unbounded Telegram history can consume large memory/network time and produce unstable automation. Cursor payloads also must not expose Telegram credentials such as `access_hash` or `file_reference`.

## Decision

All full-account/full-history reader APIs are bounded:

```text
default page = 100
max page = 500
```

Cursor rules:

- opaque base64url token;
- HMAC-SHA256 integrity;
- version + method + query fingerprint + safe continuation position;
- no `access_hash`, `file_reference`, Session/credential;
- tamper/query mismatch → `INVALID_CURSOR`;
- continuation entity unavailable → `CURSOR_STALE`.

Dialogs use stable canonical ordering; message history is newest→older. Basic Group→Supergroup history uses current→legacy composite segments and `(source_chat_id,message_id)` identity.

## Why

- predictable resource use for Codex;
- no accidental unlimited account scrape;
- safe cross-process/daemon-restart continuation;
- avoids exposing Telegram credential-like metadata;
- stable pagination is easier to test for overlap/gap.

## Alternatives Considered

### `limit=None` / read everything

Rejected: unbounded network/memory/latency and poor automation safety.

### Raw Telegram offsets/access hashes in CLI cursors

Rejected: leaks internal/credential-like Telegram data and couples CLI protocol to Telethon internals.

### Activity-order dialogs pagination

Rejected as default completeness order because new incoming messages can reshuffle pages and cause gaps/duplicates.

## Consequences

Clients must follow `next_cursor` until `has_more=false`. Search may stop after a bounded candidate scan and continue via cursor instead of scanning the whole account in one request.

## Risks

Cursor semantics are a compatibility contract. Any query/model change must preserve versioning and explicit stale/invalid errors rather than guessing.