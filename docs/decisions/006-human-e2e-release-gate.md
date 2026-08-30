# ADR-006 — Human acceptance before user-visible major Release

## Status
Accepted

## Context
GitHub CI/mock 无法验证真实 Telegram Session、权限、dialogs、Forum、匿名 sender 等账号特有行为。

## Decision
重大 Telegram runtime Candidate 在正式 Release 前必须先通过完整 Windows CI，再等待用户明确 human acceptance / release authorization。正式发布随后仍需从 final main 重新跑 Release workflow，并核验实际 Release/tag/assets/hash。

## v0.3.0 record

Frozen Candidate `7e6f62d...` / run `33296790070` 通过，用户于 2026-08-30 明确宣布验收通过；formal workflow `33299040904` success，v0.3.0 已发布。

## Consequences
CI green 不能自动等同“可发布”；Candidate Artifact 不能冒充正式 Release。
