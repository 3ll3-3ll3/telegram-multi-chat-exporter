# ADR-006 — v0.3 Requires Human Telegram E2E Before Merge/Release

## Status

Accepted for v0.3 Candidate.

## Context

GitHub Actions can exercise unit/mock logic, Windows packaging, local OS Session locks and smoke tests, but it cannot safely use the user's real Telegram credential/session. Telegram behavior for real dialogs, participant permissions, Saved Messages, Forum, migration history and anonymous/send-as identities still requires a real account.

## Decision

v0.3 uses a hard two-stage gate:

```text
Automated Candidate gate green
→ frozen, hash-traceable Windows Candidate
→ user real-account E2E
→ fix only actual failures + re-test affected scenarios
→ user explicitly authorizes release
→ merge/release
```

Before E2E PASS + explicit authorization:

- PR #20 remains Draft;
- do not merge it;
- do not create/overwrite `v0.3.0` Release;
- do not keep adding unrelated features;
- do not treat an Actions Artifact as Production.

The frozen E2E Candidate and its hashes/run IDs are recorded in `HANDOFF.md`.

## Why

CI green proves the local contract and packaging, not Telegram's real account semantics. Freezing the Candidate also ensures the user tests the same runtime that is intended for release.

## Alternatives Considered

### Release immediately after CI

Rejected for v0.3 because the new reader/daemon architecture has a much wider real-account surface than v0.1.x.

### Use real Telegram credentials in GitHub Actions

Rejected: unacceptable secret/account risk.

### Continue adding features while awaiting E2E

Rejected: invalidates the frozen candidate and increases the test surface.

## Consequences

Progress may pause while awaiting user testing. Any runtime fix after E2E failure requires regression tests, Windows CI and affected real-scenario revalidation.

## Risks

Documentation-only commits after the frozen runtime can make branch tip differ from tested runtime; `HANDOFF.md` must state both clearly.