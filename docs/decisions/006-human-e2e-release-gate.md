# ADR-006 — Human Windows / Telegram E2E Is a Release Gate

## Status
Accepted。v0.3.0 已实际履行并发布；v0.3.1 runtime patch 继续复用。

## Context
GitHub Actions 能验证 unit/mock、Windows packaging、OS Session lock、native exit code 和 smoke，但不能安全使用用户真实 Telegram credential/session，也不能访问用户真实 `%APPDATA%` 日志/状态。

## Decision
高影响 Telegram/runtime release 使用两阶段 gate：

```text
Automated Candidate green
→ frozen/hash-traceable Windows Candidate
→ required local Windows / real-account acceptance
→ fix actual failures + regression + revalidate affected cases
→ user explicit merge/release authorization
→ merge + formal Release workflow
```

v0.3.0 已按此流程完成并成为 Production。v0.3.1 PR #24 在本地 human PASS + 用户明确授权之前保持 Draft，不 merge，不发布；Actions Artifact 不是 Production。

CI 永不放真实 Telegram credentials。

## Alternatives rejected
- CI green 立即 release：不能证明真实 Telegram account semantics；
- GitHub Actions 使用真实 Telegram credentials：秘密/账号风险不可接受；
- human acceptance 期间继续无关 feature churn：会让 frozen candidate 失去意义。

## Consequences
真实账号/Windows 项必须明确标注“人工 pending”，不得伪造成 CI PASS。Runtime 修改后需重新跑 CI，并至少复验受影响真人场景。