# ADR-003 — Bounded Reader pagination and safe cursors

## Status
Accepted

## Context
全账号历史可能巨大，不能无界加载；cursor 不能泄露 Telegram credential。

## Decision
Reader default page 100、max 500；cursor opaque/HMAC/query-bound，不包含 access_hash/file_reference/Session secret。dialogs stable order，history newest→older，migration 用 current→legacy composite segment。

## Why
控制内存/IPC/Telegram 请求规模，并防止 cursor 被篡改或跨查询误用。

## Consequences
客户端必须显式分页；invalid/tampered/stale cursor 返回结构化错误，不静默重头扫描。
