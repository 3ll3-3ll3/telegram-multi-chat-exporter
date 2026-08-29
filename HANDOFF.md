# HANDOFF.md

> 当前开发交接快照。任何 Agent 接手前先读 `AGENTS.md`，再读本文件。

更新时间：2026-08-29

## 1. 当前正式版本

- 当前正式版：**TG Exporter v0.1.9**
- Release：`https://github.com/3ll3-3ll3/tg-exporter/releases/tag/v0.1.9`
- PR：`#16`
- merge commit / Release target：`22014f5999867e5d0b0e6c1e46320320fc974cd0`
- Release workflow：`33258806323`，结论 success

正式资产 SHA-256：

- `TGExporter-v0.1.9-windows-x64.exe`
  - `b2e349a7165de106f3f338df1fa44061b152ad70b0c1d71370c81758b98529cf`
- `TGExporter-v0.1.9-windows-x64-portable.zip`
  - `42af909157a624d5bc58fddb60b4f4bf6a520d9fe017a7ba115dbd2ea84f3d22`
- `tgctl.exe`
  - `028fee5cec1ec6d28edee5e51a605a1560bca9188636d10dec37abc0eb35de53`

## 2. 已确认的真人状态

用户在 2026-08-29 明确反馈 v0.1.8 上一轮功能“都验证通过”。因此以下视为真实账号通过：

- 软件内 Export Category 创建/保存/目录自动生成；
- `output/category/group/timestamp.json` 长期目录结构；
- 群分类分配与重启持久化；
- migrated legacy Basic Group catalogue 折叠；
- 当前 Supergroup 不消失、不退群、不被修改；
- 跨 migration date-range 旧+新历史读取；
- 旧 Session/settings 升级复用。

更早已真人验证：Telegram API 登录、Windows system proxy/Clash transport、Session 保存复用；qasync/shutdown 历史问题已有修复。

v0.1.9 的 tgctl 真人 E2E 当前仍由用户本机测试中；CI/mock 不能替代真实 Session/search/forward/send 验证。

## 3. v0.1.9 当前架构

```text
GUI ───────→ TelegramService ─→ Telethon SQLiteSession
tgctl ─────→ TelegramService ─→ Telethon SQLiteSession
```

两个入口使用同一 `%APPDATA%\TelegramMultiChatExporter\telegram.session`，因此由 OS-level `SessionLease` 保证同时只有一个进程直接打开 Session。

结果：

```text
GUI owns → tgctl SESSION_BUSY
tgctl owns → GUI SessionBusyError
```

这仍是 v0.1.9 正式行为。

## 4. v0.1.9 tgctl 安全边界继续有效

正式命令：

```text
tgctl status
tgctl chats list
tgctl messages search
tgctl messages get
tgctl forward
tgctl send
```

继续保持：

- `--json` stable envelope/error code；
- tgctl 不重新做 phone/OTP/2FA 登录；
- 同名 chat 返回 `AMBIGUOUS_CHAT`；
- forward 是真正 Telegram forward；
- send 只发纯文本；
- forward/send 有 `--dry-run`；
- forward 默认 20，显式 large batch 后 hard cap 200；
- FloodWait 不 retry storm；
- write 日志不记录正文；
- 真人写测试只优先 Saved Messages。

## 5. 当前设计分支

分支：

```text
design/single-daemon-ipc-v1
```

本分支当前是**架构设计分支，不是运行代码实现分支**。

用户于 2026-08-29 明确要求开始设计之前讨论的“方案 1”：

```text
single Telegram daemon owns Session
├─ GUI IPC client
├─ tgctl IPC client
└─ future MCP IPC client
```

完整设计：

```text
docs/DAEMON_IPC_DESIGN.md
```

目标版本建议：**v0.2.0**。

当前设计 PR 合并也不应改变 v0.1.9 二进制行为；实际实施必须另起实现阶段/提交并跑完整 Windows CI。

## 6. 已接受的 daemon 设计核心

### Session ownership

迁移完成后只有 daemon 创建 `TelegramService/TelegramClient` 并获得现有 `SessionLease`。

GUI/tgctl 不再直接打开 SQLiteSession。旧 v0.1.9 进程若仍占用 Session，daemon 仍应通过现有 lock 返回 `SESSION_BUSY`，不得复制 Session 或绕过锁。

### IPC

首选 Windows Named Pipe：

```text
multiprocessing.connection AF_PIPE
```

仅使用 `send_bytes/recv_bytes` 传 UTF-8 JSON，禁止 pickle object transport，不开 TCP/Web Server。

IPC identity/auth secret 只保存在兼容 AppData，不进日志/Git/stdout。

### daemon lifecycle

- 按需自动启动；
- 不注册 Windows Service；
- 不开机常驻；
- 不实现 24/7 listener/event rules；
- GUI 可持有 client lease；
- 无 lease/job/request 后 idle timeout 自动退出；
- daemon crash 后 read-only RPC 最多自动恢复/重试一次；
- write RPC 传输中断绝不自动重试，返回 `WRITE_OUTCOME_UNKNOWN`。

### GUI export

不能把几千/几万条导出消息作为一个巨大 Pipe response 传回 GUI。

设计为：

```text
GUI submit GroupExportPlan/batch
→ daemon export job
→ daemon 内 Telegram fetch
→ daemon 内 atomic JSON write
→ daemon 内 checkpoint
→ optional Option B read ack
→ GUI 只 poll progress/result
```

这样继续保证：

```text
JSON success → checkpoint → optional read ack
```

### write safety

未来 tgctl/MCP 都可能绕过 CLI parser 直接进入 IPC，因此 daemon 本身必须再次验证：

- dry-run；
- forward 20/200 cap；
- destination/chat ambiguity；
- allowed media scope；
- FloodWait stop；
- no-message-body logging。

## 7. 设计阶段明确不做

本设计阶段不实施：

- MCP Server；
- Windows Service；
- TCP/Web Server；
- 24/7 Telegram 监听；
- 自动规则转发；
- AI Agent/classifier；
- 第二 Telegram Session；
- Bot API；
- 媒体发送/媒体转发；
- 联系人/群/管理员管理；
- 消息删除。

MCP 未来只应作为 same IPCClient 上的一层薄 adapter。

## 8. 推荐实施阶段

按 `docs/DAEMON_IPC_DESIGN.md`：

1. Phase A：AF_PIPE transport/protocol + fake backend；
2. Phase B：daemon owns TelegramService，先迁 tgctl；
3. Phase C：迁 GUI read/auth/avatar；
4. Phase D：迁 GUI export job；
5. Phase E：lifecycle/crash recovery/PyInstaller；
6. Phase F：v0.2.0 candidate + 用户真人 E2E。

不能在 Phase B 只迁 tgctl 后就声称已经解决 GUI/tgctl Session ownership；只有 GUI export/auth 等也全部不再直接创建 TelegramClient，架构迁移才完整。

## 9. v0.2.0 Release gate（设计）

至少满足：

- 只有 daemon 获得生产 SessionLease；
- GUI/tgctl 都通过 IPC；
- GUI + tgctl 并发 read 不再正常返回 SESSION_BUSY；
- GUI 导出语义、migration、Option B 全部回归；
- tgctl v0.1.9 user-facing JSON/exit code 基本兼容；
- daemon 端也 enforce write safety；
- write transport failure 不 auto retry；
- daemon crash/restart 可恢复；
- 无 TCP/Web server；
- 无真实 Telegram Secret 进入 CI；
- Windows packaged smoke 全绿；
- 真人 Telegram 写操作仍只由用户本机验收。
