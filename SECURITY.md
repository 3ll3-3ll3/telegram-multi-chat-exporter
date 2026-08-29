# Security Policy

TG Exporter 处理真实 Telegram 用户账号 Session、聊天文本与 Telegram 写操作，因此默认采用：**本地最小权限、最少持久化、显式写入边界、可审计但不记录正文**。

## Sensitive data that must stay local

以下内容不得提交到 GitHub、Issue、PR、CI log 或公开文档：

- Telegram `api_hash`
- 手机号
- 登录验证码 / OTP
- 2FA 密码
- `*.session` / session journal / Session 内容
- 用户真实聊天正文或导出文件
- 用户真实群头像缓存二进制

## Local runtime files

兼容目录固定：

```text
%APPDATA%\TelegramMultiChatExporter\
```

可能包含：

```text
api_credentials.json
telegram.session
telegram.session-journal
telegram.session.lock
local_state.json
settings.json
logs\app.log
cache\avatars\*
```

这些都不是发布资产。品牌改名不得擅自迁移该目录导致 Session/设置失效。

`telegram.session.lock` 只是 Session ownership 的锁载体；安全性来自 OS-level file lock，不从文件存在性推断占用，也不得通过删 lock file 绕过并发保护。

## Logging rules

日志允许记录：

- 阶段/动作类型；
- 安全的 error type/message；
- proxy safe label / host / port；
- api_id（不是 api_hash）；
- chat_id / message_id；
- 数量、text length、成功/失败；
- catalogue migration collapse count。

日志禁止记录：

- api_hash；
- phone / OTP / 2FA；
- Session 内容；
- **message body**；
- 头像二进制/base64。

`tgctl messages search/get --json` 返回的消息正文属于用户明确请求的 stdout 数据，可以输出给调用者，但不得复制进普通 `app.log`。

新增 debug 日志前必须检查对象的 `repr()` 是否可能泄露正文或 Secret。

## Telegram read operations

以下 `tgctl` 命令属于 read operation，可直接执行：

```text
status
chats list
messages search
messages get
```

它们不得偷偷发送 read acknowledgement、消息、转发或其他 Telegram 写入。

GUI 的刷新、Chat Folder、头像读取、普通导出同样默认不改变 Telegram read marker。

## Telegram write operations

v0.1.9 起，用户明确授权第一版 `tgctl` 提供两类写操作：

```text
forward
send
```

### forward

- 必须使用 Telethon 真正 `forward_messages`；
- 不得静默变成“读取正文 → send_message”；
- 第一版只允许纯文本/普通网页预览消息；媒体消息不真正转发；
- 支持 `--to me` Saved Messages；
- 支持 `--dry-run`；
- 默认最多 20 条；显式 `--allow-large-batch` 后最多 200 条；
- 同名 chat 必须返回 `AMBIGUOUS_CHAT`，不得 first-match；
- FloodWait 不做自动 retry storm。

### send

- 第一版只发送用户命令中显式提供的纯文本；
- `parse_mode=None`；
- 不发送文件、图片、语音等媒体；
- 支持 `--dry-run`；
- 日志只记目标、安全 id、text length、结果，不记正文。

### Codex safety invariant

未来 Agent/Codex 集成**不得擅自绕过**：

```text
dry-run capability
forward batch limits
chat ambiguity rejection
FloodWait structured stop
Session lock
no-message-body logging
```

本 CLI 不弹 GUI 确认，以便 Codex 可调用；推荐产品交互是：**先 dry-run → 把结果给用户看 → 用户明确确认 → 再执行真实写操作**。

不要自行对陌生人/陌生群做真人写测试。真实 E2E 优先 Saved Messages。

## GUI read acknowledgement

GUI 的 `导出后标已读` 是另一类已有写操作，仅在用户按群明确开启 current-unread Option B 后执行：

```text
JSON success → checkpoint success → optional read ack
```

导出失败绝不改变 read marker。tgctl v0.1.9 不提供 mark-read 命令；未来若增加必须重新套用明确 write-operation 安全边界。

## Shared Session ownership

Telethon 默认 SQLiteSession 不允许 GUI/tgctl 两个进程并发拥有同一 Session。

v0.1.9 起由 `TelegramService` 获取 OS-level `SessionLease`：

- GUI 占用时 tgctl 返回 `SESSION_BUSY`；
- tgctl 占用时 GUI 给出友好 busy 错误；
- 不复制 Session、不建立隐藏第二 Session、不绕过锁。

未来 MCP/多客户端并发应采用 **single local Telegram daemon owns Session + IPC**，而不是让每个客户端自己打开 SQLiteSession。

## Build and release

GitHub Actions 不需要 Telegram Secret。CI 的 Telegram write tests 必须 mock Telethon；不得把真实账号凭据放进 Actions Secret 来跑写操作 E2E。

正式发布资产从 v0.1.9 起至少包括：

```text
TGExporter-vX.Y.Z-windows-x64.exe
TGExporter-vX.Y.Z-windows-x64-portable.zip
tgctl.exe
SHA256SUMS.txt
```

正式入口：

```text
https://github.com/3ll3-3ll3/tg-exporter/releases/latest
```

## Explicitly out of scope

当前不得顺手增加：MCP、Web Server、云端 Telegram 服务、Bot API、24/7 listener、自动转发规则、AI 分类器、联系人/群/管理员管理、消息删除、媒体发送/媒体转发、360 绕过或代码签名。

## Vulnerability / accidental secret response

如果发现 Secret 被误提交：

1. 立即停止传播。
2. 不要认为普通删除 commit 就足够，Git 历史可能仍包含数据。
3. 撤销/轮换凭据或 Session。
4. 清理 Git 历史或走 GitHub 敏感数据处理流程。
5. 在 `HANDOFF.md` 记录非敏感事件摘要与后续要求。
