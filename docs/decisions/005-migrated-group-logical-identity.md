# ADR-005 — Migrated groups use current logical identity plus legacy source identity

## Status
Accepted

## Context
Telegram Basic Group 迁移为 Supergroup 后可能同时存在 current 与 legacy peer；按标题去重会误伤真正同名聊天。

## Decision
catalogue 只展示 current logical Supergroup；legacy peer 只通过 Telegram migration metadata 关联用于历史。历史消息保留 `chat_id=current logical` + `source_chat_id=legacy/current source`，唯一定位 `(source_chat_id,message_id)`。

## Why
避免重复 UI、同名误合并，同时保留迁移前历史。

## Consequences
current-unread/read-ack 只作用 current logical Supergroup；date/history/search 才按 migration relation 跨 legacy。
