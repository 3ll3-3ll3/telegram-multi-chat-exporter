# Security Policy

TG Exporter 处理真实 Telegram 用户 Session、聊天正文和少量用户明确授权的副作用。默认原则：**local-only、single Session ownership、default read-only、least persistence、explicit writes、safe logs**。

完整架构化信任边界与 Production 规则见 [`docs/SECURITY_MODEL.md`](docs/SECURITY_MODEL.md)。本文件保留最重要的操作政策。

## Sensitive data must stay local

不得进入 GitHub、Issue、PR、CI log、普通 app log、Release notes：

- Telegram `api_id` / `api_hash`；
- phone；
- OTP / 登录验证码；
- 2FA 密码；
- `*.session` / session journal / Session 内容；
- credentials 原文；
- IPC auth secret；
- Telegram `access_hash`；
- Telegram `file_reference` bytes；
- 用户真实聊天正文/导出 JSON；
- 真实头像 cache 二进制。

用户明确执行 history/search/get 等 reader 命令时，消息正文可出现在**该命令 stdout JSON/JSONL**，但仍不得写入普通日志。

## Local runtime

兼容目录固定：

```text
%APPDATA%\TelegramMultiChatExporter\
```

可能包含 credentials、`telegram.session`、OS lock、settings/state、logs、avatar cache、v0.3 daemon identity/job metadata。

禁止：

- 品牌改名时迁移/清空该目录；
- 删除 lock 文件绕过 Session ownership；
- 复制 Session 来实现并发；
- 把这些文件打入 Release/Artifact。

## Logging allowlist

普通日志只记录 safe action/stage/error code、proxy safe label、safe chat/message/topic IDs、数量、耗时、text length、success/failure。

禁止记录：api_id/api_hash、phone/OTP/2FA、Session/credentials、IPC secret、access_hash/file_reference、message body/caption、URL text、media filename、未经 safe mapper 的 raw TL object repr。

## Telegram reads

v0.1.x read commands、GUI refresh/export，以及 v0.3 reader 的 account/dialogs/members/history/search/topics/media metadata 都不得偷偷产生 Telegram write/read-ack。

Reader 默认 read-only；Secret Chat、已删除内容恢复、无权内容绕过不属于能力范围。

## Telegram writes

当前批准的 Telegram writes：

### `forward`

- Telegram true forward；
- `--dry-run`；
- 默认 <=20；explicit large hard cap <=200；
- ambiguous target → `AMBIGUOUS_CHAT`；
- FloodWait structured stop，不 retry storm。

### `send`

- 纯文本；
- `parse_mode=None`；
- `--dry-run`；
- 不发送媒体。

### GUI optional read acknowledgement

仅 current-unread 且用户按群明确开启。固定：

```text
JSON atomic success
→ checkpoint
→ optional read acknowledgement
```

失败导出绝不标已读。

### Daemon-era write rules

v0.2/v0.3：export 活跃时 real send/forward → `EXPORT_IN_PROGRESS`，不得排队后偷偷发送。

Write request 已提交后 transport outcome unknown → `WRITE_OUTCOME_UNKNOWN`，不得自动 retry。

真人 write E2E：先 dry-run，用户确认后执行；优先 Saved Messages，不自行向陌生目标发消息。

## Session ownership

### Production v0.1.10

GUI/tgctl 是 direct-session clients，但使用 OS `SessionLease` 互斥。冲突安全返回 `SESSION_BUSY`；packaged tgctl native exit code 必须是 8。

### v0.2/v0.3 Candidate

Daemon 是唯一 TelegramClient/Session owner；GUI/tgctl 使用 authenticated Windows Named Pipe + UTF-8 JSON bytes。禁止 direct fallback、pickle transport、TCP/HTTP listener。

同代 GUI+tgctl 正常共存；`SESSION_BUSY` 仅是旧 direct process 已持锁的兼容边界。

## Explicit media download

v0.3 normal reader metadata-only。

真实 download 必须：plan → confirmation token → confirm；第一次不创建 output dir、不下载。Normal <=20 files/500 MiB；explicit large <=200 files/5 GiB；`.part` 成功后原子 rename；path traversal safety；unknown transport outcome 不自动 retry。

## GitHub / Release

- 不直接 push/force-push `main`；
- 不删除/移动历史 tag；
- 不覆盖既有 Release；
- Actions Artifact 不是正式 Production；
- GitHub Actions 不保存真实 Telegram credentials；
- v0.3 human E2E PASS + 用户明确授权前，不 merge PR #20，不创建/覆盖 v0.3.0 Release。

仓库当前没有 branch protection，因此以上纪律必须由 Agent 自行遵守。

## Out of scope

未经用户重新授权并重新做安全设计，不增加：MCP Server、Web/TCP/Cloud service、Bot API、24/7 listener、自动转发规则、AI 自主分类、联系人/群/管理员管理、删除消息、退群、修改 Chat Folder、Secret Chat、deleted recovery、permission bypass、media send/forward。

360/杀软误报/代码签名当前明确降优先级，不是开发主线。

## Accidental secret response

发现 Secret 误提交：停止传播 → 轮换 credential/Session → 必要时清理 Git 历史 → HANDOFF 只保存非敏感事件摘要。