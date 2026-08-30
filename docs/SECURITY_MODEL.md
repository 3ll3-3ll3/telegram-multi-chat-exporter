# Security Model

本文件描述 TG Exporter 的**信任边界、Production 定义、高风险操作和永久安全约束**。具体漏洞报告/敏感信息规则同时见根目录 [`SECURITY.md`](../SECURITY.md)。

## 1. Production 不是云环境

TG Exporter 当前没有远程生产数据库、云服务器、Web API 或托管后台。

本项目的 Production 资产是：

```text
GitHub 正式 Release 二进制
+
用户本机 %APPDATA%\TelegramMultiChatExporter\
+
用户真实 Telegram 账号
+
用户选择的导出目录
```

因此以下概念在本项目中**不存在**：生产 D1/Postgres、云端 migration、生产 Secret Manager、远程数据库恢复。未来 Agent 不得因为其它项目经验而擅自引入这些设施。

## 2. 本机敏感资产

兼容目录固定：

```text
%APPDATA%\TelegramMultiChatExporter\
```

可能包含：

```text
api_credentials.json
telegram.session
telegram.session-journal / lock
tg-daemon.lock
ipc_identity.json
settings.json
local_state.json
job metadata
logs/app.log
cache/avatars/
```

它们都不是 GitHub/Release 资产。

永久规则：

- 不删除/迁移整个 AppData 目录来“修问题”；
- 不复制 Telegram Session 以绕过并发；
- 不通过删除 lock 文件绕过 OS ownership；
- 品牌改名不迁移兼容路径；
- 任何清理/重置 Session 的行为必须是用户明确选择的功能，而不是后台维护动作。

## 3. 永远不能进入 GitHub/普通日志的内容

不得提交到源码、Issue、PR、Actions log、Release notes 或普通 `app.log`：

- Telegram `api_id` / `api_hash`；
- 手机号；
- OTP / 登录验证码；
- 2FA 密码；
- `*.session` / Session 内容；
- credentials 原文；
- IPC auth secret；
- Telegram `access_hash`；
- Telegram `file_reference` bytes；
- 用户真实聊天正文/导出 JSON；
- 用户真实头像 cache 二进制。

用户明确执行 `messages history/search/get` 等 reader 命令时，正文可以出现在**该命令 stdout JSON/JSONL**；这不授权普通日志记录正文。

普通日志允许安全 metadata：action/stage、safe error code/class、safe chat/message/topic ID、数量、耗时、text length、成功/失败。

禁止普通日志：message body、caption、URL 文本、media filename、未经 safe mapper 的 raw Telethon/TL object `repr()`。

## 4. 稳定版 v0.1.x Session trust boundary

正式 v0.1.10 仍是 direct-session 架构：GUI 与 tgctl 都可使用同一个 Telethon SQLiteSession，但通过 `SessionLease` 互斥。

```text
GUI ───────┐
           ├→ TelegramService → telegram.session
 tgctl ────┘
```

同一时刻只能有一个 direct owner。冲突必须安全失败：

```text
SESSION_BUSY
native exit code = 8 (packaged tgctl)
```

禁止为了支持并发而绕锁、复制 `.session` 或创建隐藏第二 Session。

## 5. v0.2/v0.3 daemon trust boundary

Candidate 采用：

```text
GUI ─┐
     ├→ authenticated local Named Pipe → TG daemon → one Telegram Session
 tgctl┘
```

- daemon 是唯一 TelegramClient/Session owner；
- GUI/tgctl 不 fallback direct Session；
- IPC 使用 Windows Named Pipe / `AF_PIPE`；
- payload 只传 UTF-8 JSON bytes；禁止 pickle object transport；
- 不监听 TCP/HTTP/LAN；
- auth secret 存本机，不进入 stdout/log/Git；
- 安全目标是防误连接/普通跨用户连接，不声称抵抗已经获得当前 Windows 用户 AppData 读取权限的恶意程序。

v0.3 GUI 与 v0.3 tgctl 正常可共存；`SESSION_BUSY` 仅用于旧 direct binary/其它 legacy process 已 OS-lock Session 的兼容边界。

## 6. 操作副作用分类

v0.3 按副作用分类：

### LOCAL

`status/job/heartbeat/cursor validation` 等，仅本地状态。

### TELEGRAM_READ

```text
account get
dialogs list
chats get/chats members
messages history/search/get
topics list/history
media metadata
```

必须保持 Telegram read-only：不 send、不 forward、不 delete、不退群、不改 Folder、不投票、不 mark-read、不自动下载媒体。

### LOCAL_DISK_WRITE

- GUI JSON export；
- 用户显式确认的 `media download`。

### TELEGRAM_WRITE

已批准边界只有：

- `forward`；
- `send`；
- GUI current-unread 的 optional read acknowledgement。

### GUI_AUTH

phone/OTP/2FA/API 配置只属于 GUI；tgctl/Codex 不获得登录交互能力。

## 7. Telegram write safety

`forward`：Telegram true forward，不允许静默退化成复制正文 + send。

`send`：纯文本，`parse_mode=None`。

必须保留：

- `--dry-run`；
- forward 默认最多 20；explicit large hard cap 200；
- 同名/模糊目标 `AMBIGUOUS_CHAT`，不 first-match；
- FloodWait structured stop，不 retry storm；
- export 活跃时 real send/forward → `EXPORT_IN_PROGRESS`，不排队后自动发送；
- 请求已送入 daemon 后 transport 中断 → `WRITE_OUTCOME_UNKNOWN`，绝不自动 retry。

真人 write E2E：先 dry-run，用户确认后再执行；优先 Saved Messages，不自行向陌生群/联系人发消息。

## 8. Read acknowledgement safety

GUI “导出后标已读”默认 OFF，只能用于 current-unread。

固定顺序：

```text
JSON atomic success
→ checkpoint success
→ optional read acknowledgement
```

导出失败绝不标已读；read-ack 失败不删除已成功 JSON。

Reader 命令不得暗中复用该写能力。

## 9. Explicit media download

默认 reader 仅 media metadata，不下载。

真实下载必须两阶段：

```text
plan
→ DOWNLOAD_CONFIRMATION_REQUIRED + token
→ no output dir / no download

confirm same plan
→ bounded download
→ *.part
→ success: atomic rename
```

限制：normal 20 files / 500 MiB；explicit large 最大 200 files / 5 GiB。未知大小也按实际累计 bytes 执行 hard cap。

文件名只取 safe basename 并防 path traversal。confirmed request transport outcome unknown 不自动 retry。

## 10. Identity / Telegram truthfulness

- owner/admin/member 只依据 Telegram participant/admin data；
- role 是查询时 current snapshot，不伪造历史管理员任期；
- anonymous admin/send-as 不从显示名、`post_author` 或管理员表反推个人；
- 权限不足时返回 unavailable/access denied，不拿消息作者集合冒充成员表；
- 查不到 message 只能说 `not_found_or_unavailable`，不能自动标记 deleted；
- URL domain filter 只做 hostname parsing，不访问目标 URL、不 follow redirect。

## 11. Migration safety

Basic Group → Supergroup：

- current Supergroup 是 logical entity；
- legacy Basic Group 仅作历史 source；
- 不按同名猜 migration；
- 不删除/退群/降级/修改真实 Supergroup；
- 唯一消息键 `(source_chat_id,message_id)`；
- legacy history 的 current-role snapshot 基于 current logical Supergroup。

## 12. GitHub / Release safety

- 不直接 push/force-push `main`；
- 不移动/删除历史 tags；
- 不覆盖既有 Releases；
- Actions Artifact 不是 Production；
- GitHub Actions 不放真实 Telegram credentials；
- v0.3 真人 E2E + 用户明确授权前不 merge PR #20、不创建/覆盖 v0.3.0 Release。

仓库目前没有 branch protection，因此这些是**必须由 Agent 自行执行的政策**。

## 13. 明确不做

未经用户重新授权并重新做安全设计，不新增：

- MCP Server；
- TCP/HTTP/Web/Cloud server；
- Bot API；
- 24/7 listener；
- 自动转发规则 / AI 自主分类；
- 联系人/群/管理员管理；
- 删除消息、退群、修改 Chat Folder；
- Secret Chat、已删除内容恢复、绕权读取；
- 媒体发送/媒体转发。

360/杀软误报和代码签名当前由用户明确降优先级，不是主线。

## 14. Incident response

若发现 Secret 误提交：

1. 立即停止继续传播；
2. 轮换相关 API credential / Telegram Session；
3. 评估并清理 Git 历史；
4. HANDOFF 只记录非敏感事故摘要，不复制 Secret。

若发现真实 Telegram write outcome 不确定：不要自动重试，先让用户检查目标聊天。