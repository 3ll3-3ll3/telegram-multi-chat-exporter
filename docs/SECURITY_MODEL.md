# Security Model

## Trust boundary

TG Exporter 是 Windows 本地应用，没有远程 Production DB/server。主要信任边界：

```text
User / GUI / tgctl
        ↓
authenticated local Named Pipe
        ↓
TG daemon (only Telegram Session owner)
        ↓
Telethon / Telegram
```

本机 AppData、用户 Telegram 账号和用户导出目录都属于敏感本地数据边界。

## Session / credentials

兼容目录固定 `%APPDATA%\TelegramMultiChatExporter\`。禁止复制、上传、提交、日志输出或迁移 shortcut 暴露：

- `telegram.session` 内容；
- api_id/api_hash；
- phone/OTP/2FA；
- IPC auth secret；
- Telegram access_hash/file_reference。

只有 daemon 可以 direct-open Telegram Session。GUI/tgctl 不得绕过 daemon 或 SessionLease。

## IPC

- Windows Named Pipe / `AF_PIPE`；
- 本地 auth secret；
- UTF-8 JSON bytes；
- 禁止 pickle object transport；
- 不开 TCP/HTTP/Web endpoint。

## Reader vs writes

Reader 默认 read-only，不发送/转发/删除/退群/改 Folder/标已读/自动下载媒体。

真实 Telegram 写操作只允许既有边界：true-forward、plain-text send、GUI optional read-ack。forward/send 必须支持 dry-run、批量上限、无歧义目标、FloodWait stop；transport outcome unknown 不自动 retry。

Current-unread read-ack 默认 OFF，严格 `JSON success → checkpoint → optional ack`，ack 只到本次 frozen upper。

## Media download

显式 media download 是本地磁盘副作用：plan→confirmation→download；normal 20 files/500 MiB，large 最大 200 files/5 GiB；safe path；`.part` 成功后 atomic rename。

## Logging

普通日志不得记录 credential/Session、message body/caption、URL text、media filename、access_hash/file_reference。用户明确 reader 请求时正文可以出现在 stdout JSON/JSONL，但不能转存到普通 app.log。

## Production / Release protection

- 不 force-push main；
- 不删除/覆盖历史 tag/Release；
- Actions Artifact 不是 Production；
- 正式二进制只由 Release workflow 从 main 构建；
- workflow success 后仍需核验实际 Release、tag target、assets、hash；
- 不把真实 Telegram credentials 放进 GitHub Actions。

## High-risk operations

以下操作除非用户明确重新授权并重新设计安全模型，否则不实现：删除消息、退群、联系人/管理员管理、修改 Telegram Folder、绕权限读取、Secret Chat、长期自动监听、自动回复/自动转发、Web 远程控制。
