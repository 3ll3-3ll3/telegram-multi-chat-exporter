# Architecture

## Product boundary

这是一个“批次导出器”，不是归档数据库。

每次运行：

1. 用户在 GUI 中选择多个群。
2. 每个群独立选择导出规则。
3. 程序只读取该群本次规则命中的文本消息。
4. 每个群写入独立 `result.json`。
5. 所有群放进本次独立批次目录。
6. 历史批次不会被读取、合并或重写。

`local_state.json` 仅为“上次导出以后”模式保存每群一个 message id，不保存消息正文。

## Security boundary

- `api_credentials.json`：仅本机 `%APPDATA%/TelegramMultiChatExporter/`。
- `telegram.session`：仅本机同一目录。
- 仓库 `.gitignore` 明确排除 Session 与凭据。
- GitHub Actions 构建不需要任何 Telegram Secret。

## Desktop JSON compatibility

优先兼容纯文本消息常用字段：

- `id`
- `type`
- `date`
- `date_unixtime`
- `from`
- `from_id`
- `reply_to_message_id`
- `edited`
- `edited_unixtime`
- `text`
- `text_entities`

V0.1 不承诺复杂富文本实体和服务消息与 Telegram Desktop byte-for-byte 一致。
