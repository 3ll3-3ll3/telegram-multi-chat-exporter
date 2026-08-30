# ADR-007 — Current-unread snapshot is frozen at each group's export start

## Status
Accepted and implemented in v0.3.0

## Context
Catalogue refresh 可能早于某个群真正开始导出数分钟。若使用旧 read/latest state，“current unread”会漏掉实际开工前已经成为未读的消息。

## Decision
每个 current-unread 群在该群真正开始执行时获取并冻结：

```text
lower = read_inbox_max_id_at_export_start
upper = latest_message_id_at_export_start
export only lower < message_id <= upper
```

optional read-ack 只能在 `JSON atomic success → checkpoint` 后推进到同一个 frozen upper。snapshot 后到达的新消息留到下一次。迁移群 current-unread 只使用 current logical Supergroup。

## Rejected alternatives
catalogue-refresh snapshot；无 upper bound live scan；一个 batch-global snapshot。

## Consequences
语义确定且符合用户预期；Telegram read pointer 仍可能使 frozen ID 范围内未写入 JSON 的 media/service item 一并变 read，因此 Option B 默认 OFF 并保留 GUI warning。
