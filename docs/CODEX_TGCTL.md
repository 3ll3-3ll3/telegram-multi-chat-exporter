# Codex + tgctl Telegram Bridge

## 1. tgctl 是什么

`tgctl` 是 TG Exporter 的本地 Telegram CLI Bridge。它不使用 Bot API，也不创建第二套登录系统，而是复用 TG Exporter 已经登录好的 Telethon 用户 Session：

```text
用户自然语言
→ Codex
→ 本机 tgctl.exe
→ TelegramService
→ Telethon
→ 用户自己的 Telegram 账号
```

第一版只做确定性读取和用户明确要求的手动写操作；不包含 MCP、长期监听、规则自动转发、AI 分类器或后台 Agent。

## 2. 登录与本地文件

继续使用兼容目录：

```text
%APPDATA%\TelegramMultiChatExporter\
```

复用：

```text
api_credentials.json
telegram.session
Windows system proxy detection
```

如果 Session 未授权，CLI 不会索要手机号、验证码或 2FA，而是返回 `NOT_AUTHORIZED` 并提示先打开 TG Exporter 完成登录。

为了避免两个 Telethon 进程同时写同一个 SQLiteSession，GUI 与 `tgctl` 共用一个 OS 文件锁。第一版规则：

- 使用 `tgctl` 时关闭 TG Exporter GUI；
- 如果另一个进程已经占用 Session，返回 `SESSION_BUSY`；
- 不尝试绕过锁，不复制 Session，不自动创建第二 Session。

未来 MCP/多客户端并发更适合升级成单一 Telegram daemon + IPC，本版不做。

## 3. Windows 入口

正式 Release 提供独立 `tgctl.exe`，portable ZIP 内也包含 `tgctl.exe`。

开发环境同时支持：

```powershell
python -m telegram_exporter.tgctl status --json
tgctl status --json
```

Codex 最稳定的调用方式是给出 `tgctl.exe` 的绝对路径，或把它所在目录加入当前 shell PATH。

## 4. JSON 协议

所有核心命令支持 `--json`。JSON 模式 stdout **只输出一份 JSON**，普通日志进入本地日志文件，不混入 stdout。

成功：

```json
{"ok":true,"data":{}}
```

失败：

```json
{
  "ok": false,
  "error": {
    "code": "AMBIGUOUS_CHAT",
    "message": "群名对应多个聊天。请改用 chat_id。",
    "details": []
  }
}
```

稳定错误码包括：

```text
NOT_AUTHORIZED
CHAT_NOT_FOUND
AMBIGUOUS_CHAT
MESSAGE_NOT_FOUND
FLOOD_WAIT
WRITE_FAILED
INVALID_ARGUMENT
SESSION_BUSY
```

退出码：

```text
0 成功
2 参数错误
3 未登录
4 chat/message 不存在
5 chat 歧义
6 FloodWait
7 Telegram 写操作失败
8 Session 被占用
1 其他 Telegram/运行错误
```

## 5. 读取命令

### 账号状态

```powershell
tgctl status --json
```

只返回安全字段：授权状态、用户 id/显示名/username、安全 Session 标签、proxy 标签。不会输出 phone、api_hash、OTP、2FA 或 Session 内容。

### 列群/频道

```powershell
tgctl chats list --json
tgctl chats list --folder "保研" --json
tgctl chats list --search "保研" --limit 50 --json
```

每项至少包含：

```text
chat_id
title
username
type
```

复用 GUI 的 migrated Basic Group → current Supergroup collapse，因此不会重新把迁移前旧群作为重复 row 暴露给 Codex。

### 搜索消息

```powershell
tgctl messages search `
  --chat "-1001234567890" `
  --contains "预推免" `
  --since "2026-08-29T00:00:00" `
  --until "2026-08-30T00:00:00" `
  --limit 100 `
  --json
```

时间语义：`since` inclusive，`until` exclusive。没有时区的 ISO 时间按本机时区解释。

第一版支持 text/caption，不下载聊天媒体。`--case-sensitive` 可选；未实现 regex。

返回：

```text
chat_id
chat_title
message_id
date
sender
text
```

`--chat` 可以使用 chat_id、精确 `@username` 或精确群名。同名群存在多个时返回 `AMBIGUOUS_CHAT` 和候选 chat_id，绝不静默猜一个。

### 获取指定消息

```powershell
tgctl messages get --chat -1001234567890 --ids 123 456 789 --json
```

任一请求 id 不存在时返回 `MESSAGE_NOT_FOUND` 并列出 missing ids，适合 Codex 在真正 forward 前再次确认。

## 6. Telegram 写操作

`forward` 和 `send` 明确属于 Telegram write operation。CLI 不弹 GUI 确认，因为它需要被 Codex 调用；安全流程依赖 **先 dry-run → 用户确认 → 再执行真实命令**。

普通日志只记录动作类型、chat_id、message_id/数量、成功失败；不记录消息正文。

### 真正转发

```powershell
tgctl forward `
  --from -1001234567890 `
  --to me `
  --ids 123 456 `
  --dry-run `
  --json
```

`--to me` 表示 Saved Messages / 我的收藏。

确认后去掉 `--dry-run`：

```powershell
tgctl forward --from -1001234567890 --to me --ids 123 456 --json
```

使用 Telethon `forward_messages`，不是复制文本再 send。

第一版只允许纯文本消息及普通网页链接预览；图片/视频/文件/语音等媒体消息不会被 tgctl forward，相关 id 会出现在 `failed_ids`。

批量安全闸门：

```text
默认单次最多 20 条
--allow-large-batch 后最多 200 条
超过 200 条仍拒绝
```

不会因为 FloodWait 自动疯狂重试；返回 `FLOOD_WAIT` 和 `retry_after_seconds`。

### 发送纯文本

```powershell
tgctl send --to me --text "TG Exporter Codex bridge test" --dry-run --json
```

确认后：

```powershell
tgctl send --to me --text "TG Exporter Codex bridge test" --json
```

发送使用 `parse_mode=None`，第一版不发送图片、文件、语音等媒体。

## 7. 推荐 Codex Prompt

可以直接对 Codex 说：

> 使用 tgctl 查询我的 Telegram 中名称包含“保研”的群，先只读取，不执行任何写操作。请始终使用 `--json`。

> 使用 tgctl 搜索 `<chat_id>` 今天包含“预推免”的消息，按时间排序并给我摘要，不执行 Telegram 写操作。

> 使用 tgctl 对刚才结果中的第 2 和第 4 条执行 forward dry-run，目标是 Saved Messages；把 dry-run 结果给我看，不要真正转发。

> 我确认，执行刚才 dry-run 对应的转发；只转发刚才确认的 message_id，不扩大范围。

> 使用 tgctl 给 Saved Messages 发送“TG Exporter Codex bridge test”，先 dry-run，不要真正发送。

## 8. 真人 E2E Checklist

在自己的 Windows + 已登录 Telegram Session 上，关闭 TG Exporter GUI 后依次验证：

```powershell
tgctl status --json
tgctl chats list --search "保研" --json
tgctl messages search --chat <chat_id> --contains "预推免" --limit 20 --json
tgctl messages get --chat <chat_id> --ids <message_id> --json
tgctl forward --from <chat_id> --to me --ids <message_id> --dry-run --json
tgctl send --to me --text "TG Exporter Codex bridge test" --dry-run --json
```

真实写操作只在用户明确确认后，以 Saved Messages 为优先安全目标：

```powershell
tgctl forward --from <chat_id> --to me --ids <message_id> --json
tgctl send --to me --text "TG Exporter Codex bridge test" --json
```

再验证 GUI 与 CLI 同时打开时，后启动者得到 Session busy 提示，而不是 SQLite session corruption。

## 9. 安全边界

禁止从 CLI 输出或日志记录：

```text
api_hash
phone
OTP/code
2FA password
Session 内容
```

日志禁止记录消息正文。JSON 搜索结果/`messages get` 的消息正文属于命令明确请求的 stdout 数据，不写入普通日志。

第一版没有：MCP、Web server、Bot API、24/7 listener、自动规则、联系人/群管理、删除消息、管理员操作、媒体发送/媒体转发、AI 分类器。

## 10. 未来 MCP

下一阶段可以在本次 `TelegramService` abstraction 上建立 MCP Server。主要还需要：

- 单一后台 Telegram daemon，统一拥有 Session；
- GUI / tgctl / MCP 经 IPC 调用 daemon，解决并发 Session 所有权；
- MCP tool schema 与 write-operation confirmation policy；
- 长连接生命周期、崩溃恢复与客户端鉴权；
- 仍复用当前 deterministic Telegram Core，而不是把业务逻辑再复制一套。
