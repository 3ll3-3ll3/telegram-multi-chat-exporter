# ADR-001 — Single daemon owns the Telegram Session

## Status
Accepted

## Context
v0.1.x GUI 和 tgctl direct-open 同一个 Telethon SQLite Session，会产生并发锁和生命周期问题。

## Decision
v0.2+ 使用单一 local daemon，只有 daemon 创建 TelegramClient、打开 `telegram.session`、取得 SessionLease。GUI/tgctl/future clients 通过 IPC 调 daemon。

## Why
避免 SQLite Session 并发损坏/锁冲突，并让 GUI 关闭后 export 仍可继续。

## Rejected alternatives
复制 Session、给 GUI/tgctl 各建 Session、daemon 不可用时 fallback direct Session。

## Consequences
同代 GUI+tgctl 正常共存；legacy direct holder 仍通过 `SESSION_BUSY` 兼容边界阻止第二 owner。
