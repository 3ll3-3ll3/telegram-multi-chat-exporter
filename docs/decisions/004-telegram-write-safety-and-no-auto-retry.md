# ADR-004 — Telegram writes are explicit, bounded, and not blindly retried

## Status
Accepted

## Context
真实用户号 write 的误操作或重复发送代价高，transport failure 后结果可能未知。

## Decision
true-forward/plain-text send 保留 dry-run；forward 默认 20、显式 large hard cap 200；同名目标必须 AMBIGUOUS_CHAT；FloodWait 停止；请求已交给 daemon 后 transport 中断返回 WRITE_OUTCOME_UNKNOWN，不自动 retry。export 活跃时 real writes 立即 EXPORT_IN_PROGRESS。

## Why
优先可预测性和避免重复副作用。

## Consequences
调用方在 unknown outcome 后必须先检查目标状态，再决定是否重新操作。
