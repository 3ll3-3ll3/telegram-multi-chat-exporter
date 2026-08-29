# HANDOFF.md

> 当前开发交接快照。任何 Agent 接手前先读 `AGENTS.md`，再读本文件。

更新时间：2026-08-29

## 1. 当前版本状态

### 最新正式 Release

- 当前正式版：**TG Exporter v0.1.8**
- Release：`https://github.com/3ll3-3ll3/tg-exporter/releases/tag/v0.1.8`
- target：`8bd83eb2869f3843b353d727b612688d0ecfcd91`
- 正式 EXE SHA-256：`3de70bd1c70df94370e0639a81146f033db955bce638b5f5a3504c3cc4581439`
- Portable SHA-256：`9650f5e6c2c510c08821bd38ea0ff1898157321076f88708d6814c158c14057f`

### v0.1.8 真人验证状态

用户在 2026-08-29 明确反馈“上文这些都验证通过”。因此以下此前待验收项现在视为真实账号通过：

- 软件内 Export Category 创建/保存/目录自动生成；
- `output/category/group/timestamp.json` 长期目录结构；
- 群分类分配与重启持久化；
- migrated legacy Basic Group 在 catalogue 中折叠，只保留当前 Supergroup；
- 当前 Supergroup 不消失、不退群、不被修改；
- 跨 migration date-range 旧+新历史读取；
- 旧 Session/settings 升级复用。

早期已验证：Telegram API 登录、Windows system proxy/Clash transport、Session 保存复用；qasync/shutdown 历史问题已有修复。

## 2. 当前开发分支：tgctl v1

分支：`codex/tgctl-v1`

目标版本：**v0.1.9**。

用户明确要求增加“Codex 可调用的本地 Telegram CLI Bridge”，本版不做 MCP/daemon/监听/规则引擎/AI Agent。

目标：

```text
用户
→ Codex
→ tgctl.exe
→ 共享 TelegramService
→ 现有 TG Exporter Session / proxy
→ Telethon user account
```

## 3. v0.1.9 candidate 已实现

### CLI

开发入口：

```text
python -m telegram_exporter.tgctl ...
tgctl ...
```

正式 Windows 计划额外发布 standalone `tgctl.exe`，portable ZIP 内也包含 `tgctl.exe`。

核心命令：

```text
tgctl status
tgctl chats list
tgctl messages search
tgctl messages get
tgctl forward
tgctl send
```

核心命令支持 `--json`，协议：

```json
{"ok":true,"data":{}}
{"ok":false,"error":{"code":"...","message":"...","details":{}}}
```

错误码包括：`NOT_AUTHORIZED / CHAT_NOT_FOUND / AMBIGUOUS_CHAT / MESSAGE_NOT_FOUND / FLOOD_WAIT / WRITE_FAILED / INVALID_ARGUMENT / SESSION_BUSY`。

### Session / login

- 继续复用 `%APPDATA%\TelegramMultiChatExporter\api_credentials.json`；
- 继续复用 `%APPDATA%\TelegramMultiChatExporter\telegram.session`；
- 复用现有 Windows system proxy detection；
- tgctl 不重新实现 phone / OTP / 2FA 登录；未授权时提示先打开 GUI 登录；
- `TelegramService` 新增 OS Session lock；GUI 与 CLI 同时打开时后启动者应得到 `SESSION_BUSY`，避免两个 Telethon SQLiteSession 客户端同时打开真实 session。

### Read operations

- `status`：只输出 user id/display name/username、安全 Session 标签、proxy 标签；不输出 phone/api_hash/OTP/2FA/session contents。
- `chats list`：复用 `list_groups()`、Telegram Chat Folder membership 和 migration collapse；支持 `--folder / --search / --limit`。
- `messages search`：支持 chat、contains、since、until、limit、`--case-sensitive`；只输出 text/caption，不下载媒体。
- `messages get`：按 ids 精确获取；缺失 id 返回 `MESSAGE_NOT_FOUND`。
- chat reference 支持 marked chat_id、精确 @username、精确 title；同名 title 返回 `AMBIGUOUS_CHAT` 候选，不静默选择。

### Write operations

- `forward` 使用 Telethon 真正 `forward_messages`，支持 `--to me` Saved Messages；不是 copy text + send。
- 第一版 forward 只允许纯文本/普通网页 preview；图片/视频/文件/语音等 media id 进入 `failed_ids`，不做媒体转发。
- `send` 只发送纯文本，`parse_mode=None`。
- forward/send 都支持 `--dry-run`。
- forward 默认最多 20 条；显式 `--allow-large-batch` 后最多 200 条；超过仍拒绝。
- FloodWait 不自动疯狂重试，CLI 映射为结构化 `FLOOD_WAIT` + `retry_after_seconds`。
- 写日志只记录动作、chat/message id、数量、成功失败、text length；不记录正文。

## 4. v0.1.9 candidate 测试

新增 `tests/test_tgctl.py` / `tests/test_session_lock.py`，覆盖：

- CLI 参数解析；
- JSON stdout envelope；
- ambiguous chat；
- chat not found；
- deterministic search filter；
- forward dry-run 不写 Telegram；
- send dry-run 不写 Telegram且日志不含正文；
- 20/200 批量上限；
- NOT_AUTHORIZED；
- FloodWait 结构化映射；
- 输出不包含 credential fields；
- Session lock 生命周期。

Windows workflow 已改为同时构建：

```text
TGExporter.exe
tgctl.exe
```

并分别 packaged smoke-test。

正式 Release workflow 已改为：

- GUI one-file；
- GUI portable；
- standalone tgctl.exe；
- portable 内 tgctl.exe；
- 四个 packaged smoke paths；
- SHA256SUMS 包含 TGExporter one-file / portable / tgctl 三个资产。

## 5. 仍需完成后才能发布

- 最新 branch Windows CI 必须全绿；如果失败，读 Actions logs 自己修。
- README / AGENTS / ARCHITECTURE / DECISIONS / TESTING / SECURITY / RELEASE_PROCESS / CODEX_TGCTL / release notes 全部与实现一致。
- 开 PR，PR CI 全绿。
- squash merge，merge commit message 使用 `release: v0.1.9` 以触发正式 Release。
- 正式 Release workflow 全绿并核对 `tgctl.exe` asset 和 SHA256。
- Release 成功后再把本 HANDOFF 改成 v0.1.9 正式状态。

## 6. v0.1.9 真人 E2E（发布后仍需要用户账号）

CI/mock 不能替代以下真实 Telegram 验证：

1. 关闭 GUI 后 `tgctl status --json` 直接复用已有 Session，无 phone/OTP/2FA；
2. `chats list --folder` 与真实 Telegram folder 基本一致；
3. `messages search/get` 返回真实 chat text/caption；
4. forward dry-run 到 `me` 不产生 Telegram 写入；
5. 用户确认后真实 forward 到 Saved Messages；
6. send dry-run 不写入；
7. 用户确认后真实 send 到 Saved Messages；
8. GUI 已打开时 tgctl 返回 `SESSION_BUSY`，反向也同理；
9. FloodWait 真实触发时不自动循环重试（不应故意制造 FloodWait 做 E2E）。

真实写操作不要自行向陌生人/陌生群测试；Saved Messages 优先。

## 7. 三种“分组/分类”仍严格区分

- Telegram Chat Folder：账号同步，只读筛选；
- Focused workspace：GUI 工作群；
- Export Category：本地 JSON 路径分类。

`tgctl chats list --folder` 只读取第一种，不写回 Telegram，也不影响 Export Category。

## 8. 关键安全不变量

- 不输出/提交：api_hash、phone、OTP、2FA、Session contents、真实用户导出。
- 日志不记录聊天正文；CLI stdout 的 message text 是用户明确请求的数据，不进入 app.log。
- 不绕过 Session lock。
- 不让 Codex 自动扩大 write 范围。
- dry-run、批量上限、chat ambiguity、FloodWait 都是长期安全边界。
- 本版没有 MCP / daemon / 24x7 listener / auto-forward / Bot API / media write / contact/group/admin management。

## 9. 未来 MCP 方向

若下一阶段升级 MCP，优先架构：

```text
single Telegram daemon (owns session)
├─ GUI IPC client
├─ tgctl IPC client
└─ MCP IPC client
```

还需要：IPC protocol、daemon lifecycle/crash recovery、本机客户端鉴权、MCP tool schema、write confirmation policy。不要让 GUI/tgctl/MCP 三个进程各自打开同一 SQLiteSession。
