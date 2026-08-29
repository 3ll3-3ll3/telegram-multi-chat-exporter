# Single Telegram Daemon + Local IPC Design

> 状态：**Design / Not Implemented**  
> 目标版本建议：**v0.2.0**  
> 基线：TG Exporter v0.1.9  
> 本文只定义架构与迁移方案；在设计 PR 合并前，不改变现有 GUI / tgctl 运行行为。

## 1. 目标

解决 v0.1.9 的核心并发限制：GUI 与 `tgctl` 不能同时直接打开同一个 Telethon SQLiteSession，目前后启动者只能得到 `SESSION_BUSY`。

目标架构：

```text
                       ┌─────────────────────────┐
                       │   single TG daemon      │
                       │                         │
                       │  owns TelegramService   │
                       │  owns telegram.session  │
                       │  owns Telethon client   │
                       │  owns proxy/FloodWait   │
                       └────────────┬────────────┘
                                    │
                         local authenticated IPC
                                    │
                 ┌──────────────────┼──────────────────┐
                 │                  │                  │
                 ▼                  ▼                  ▼
          TG Exporter GUI        tgctl.exe       future MCP client
```

v0.2.0 第一阶段只迁移 **GUI + tgctl**。MCP 只保留兼容接口位置，不在本阶段实现。

完成后期望用户体验：

```text
TG Exporter GUI 一直打开
+
Codex 同时调用 tgctl 搜索/读取 Telegram
+
经用户确认后 tgctl forward/send
+
不再因为共享 SQLiteSession 返回 SESSION_BUSY
```

## 2. 必须保持的不变量

本架构不能以“解决并发”为理由破坏现有产品规则：

- 仍只复用 `%APPDATA%\TelegramMultiChatExporter\telegram.session`，不复制第二 Session。
- 仍复用现有 `api_credentials.json` 和 Windows system proxy detection。
- GUI 导出仍是独立 JSON，不做累计数据库。
- 输出仍是 `总输出目录 / Export Category / 群组 / YYYY-MM-DD_HH-mm-ss.json`。
- GUI 消息导出仍不下载聊天媒体；caption 可保留。
- Basic Group → Supergroup migration collapse 保持不变。
- current unread frozen snapshot、Option B 顺序保持不变。
- `tgctl` 的 JSON envelope、错误码和退出码尽量保持兼容。
- `forward` 必须是真正 Telegram forward。
- `send` 仍只允许纯文本。
- dry-run、20/200 批量闸门、AMBIGUOUS_CHAT、FloodWait stop、no-body logging 必须继续存在。
- 不增加 24/7 监听、自动转发规则、AI Agent、Bot API、联系人/群/管理员管理、删除消息、媒体发送/媒体转发。

## 3. 关键架构决策

### 3.1 Session 只有 daemon 可以打开

迁移完成后：

```text
GUI       ─┐
tgctl     ─┼─ X 不再直接创建 TelegramClient
future MCP─┘

TG daemon ─── 唯一创建 TelegramService / TelegramClient
                └─ 唯一持有 telegram.session
```

现有 `SessionLease` 不删除，而是改变职责：

- daemon 启动 TelegramService 前获取 SessionLease；
- daemon 生命周期内持续持有；
- GUI / tgctl IPC client 不再获取 SessionLease；
- 如果旧版 v0.1.9 GUI/tgctl 仍占着 Session，daemon 获取失败并向新客户端映射现有 `SESSION_BUSY`。

这样既兼容升级期间的旧进程，也避免通过删除 lock file 绕过安全边界。

### 3.2 IPC 使用 Windows Named Pipe，不开 TCP/Web Server

首选实现：Python 标准库 `multiprocessing.connection` 的 Windows `AF_PIPE`。

理由：

- 纯本机；
- 不监听 LAN；
- 不占 TCP 端口；
- 不触发防火墙端口体验；
- 无需引入 pywin32 作为第一版硬依赖；
- `Listener` / `Client` 自带 authkey challenge-response。

禁止使用 `Connection.send()` / `recv()` 传 Python 对象，因为它们依赖 pickle。协议只允许：

```text
send_bytes(UTF-8 JSON)
recv_bytes(maxlength=...)
```

即 IPC 数据始终是显式 JSON，不反序列化任意 Python 对象。

### 3.3 IPC identity 与本机鉴权

在兼容 AppData 下增加：

```text
%APPDATA%\TelegramMultiChatExporter\ipc_identity.json
```

首次原子生成：

- random installation/instance id；
- random 256-bit IPC auth secret；
- protocol identity metadata。

Pipe 名使用非敏感 instance id，例如：

```text
\\.\pipe\TGExporter-<instance-id>-v1
```

`authkey` 使用本地 secret。

威胁模型：

- 目标是阻止误连接、其他 Windows 用户或不持有本地 AppData secret 的普通进程直接调用接口；
- **不声称能够防御已经在同一个 Windows 用户权限下执行、并且能读取 TG Exporter AppData/Session 的恶意程序**。此类程序本身已经进入同一信任边界。

IPC secret 不写日志、不进 Git、不作为 CLI stdout 数据。

### 3.4 daemon 是按需后台进程，不注册 Windows Service

v0.2.0 不安装 Windows Service，也不加入开机启动。

生命周期：

```text
GUI/tgctl 发起调用
→ 尝试 IPC hello
→ daemon 不存在
→ 本机启动一个 daemon
→ daemon 获取 singleton ownership + SessionLease
→ IPC ready
→ client 正常调用
```

建议默认：

- GUI 存在活跃 client lease 时 daemon 保持运行；
- 没有 GUI lease、没有运行中 job、没有活跃请求后进入 idle；
- idle 约 5 分钟后自动退出；
- tgctl/Codex 下一次调用可自动重新启动。

这不是 24/7 Telegram listener：daemon 不注册消息事件规则，不主动监控或转发，只在客户端请求时执行确定性操作。

### 3.5 daemon singleton

新增独立 OS-level daemon owner lock，例如：

```text
%APPDATA%\TelegramMultiChatExporter\tg-daemon.lock
```

启动顺序：

```text
acquire daemon owner lock
→ initialize IPC server
→ load credentials
→ acquire existing telegram SessionLease
→ initialize TelegramService
→ serve RPC
```

两个客户端同时发现 daemon 不存在并同时尝试启动时，只允许一个 daemon 获得 owner lock；另一个候选进程立即退出，客户端继续等待同一个 Pipe ready。

不能用“lock file 是否存在”判断 daemon 是否存活，仍依赖 OS lock。

## 4. 进程与模块边界

建议新增：

```text
src/telegram_exporter/
├─ daemon_main.py          # daemon 进程入口 / lifecycle
├─ daemon_server.py        # RPC dispatch / job registry / policy
├─ ipc_protocol.py         # protocol version / envelope / validation
├─ ipc_transport.py        # AF_PIPE bytes transport
├─ ipc_client.py           # GUI/tgctl 共用 client
├─ daemon_manager.py       # ensure_running / startup / health / upgrade
├─ telegram_proxy.py       # async proxy，尽量镜像 TelegramService API
└─ export_coordinator.py   # daemon 内 export job + checkpoint + read ack
```

保留：

```text
telegram_service.py
exporter.py
```

但它们变成 **daemon/server-side core**，不再由 GUI/tgctl 直接实例化 TelegramClient。

### 4.1 为什么不把整批消息通过 IPC 发回 GUI

当前 `exporter.py` 直接使用 `TelegramClient.iter_messages()` 收集消息并生成最终 JSON。长日期范围可能产生几千/几万条消息。

错误方向：

```text
daemon 抓全部消息
→ 一个巨大 JSON response
→ Named Pipe
→ GUI 再写 result JSON
```

问题：

- frame 可能很大；
- 内存复制多次；
- 进度困难；
- daemon crash / pipe disconnect 恢复差；
- 容易把聊天正文扩大到 IPC/调试日志风险。

采用：

```text
GUI 提交 export plan
→ daemon 创建 export job
→ daemon 内调用 exporter.py + TelegramClient
→ daemon 直接原子写最终 JSON
→ GUI 只轮询 job progress/result
```

因此聊天正文不需要为了 GUI 导出跨 IPC 传输。

## 5. GUI 导出 job 模型

建议 RPC：

```text
export.batch.start
export.job.status
export.job.result
export.job.cancel        # 可先设计，v1 可延后实现真正取消
```

`export.batch.start` 参数只包含必要的结构化计划：

- output root；
- group chat id/title/type/migration id；
- Export Category；
- export mode；
- start/end；
- frozen unread bounds；
- mark_read_after_export；
- 其他现有 GroupExportPlan 必需字段。

返回：

```json
{"job_id":"..."}
```

GUI 每 200~500ms 异步轮询：

```json
{
  "state":"running",
  "current_chat_id":-100123,
  "completed_groups":2,
  "total_groups":5,
  "current_message_count":300
}
```

完成只返回小型结果：

```json
{
  "state":"completed",
  "groups":[
    {
      "chat_id":-100123,
      "message_count":820,
      "result_path":"D:\\...\\2026-...json",
      "read_ack":"success|skipped|failed"
    }
  ]
}
```

### 5.1 Option B 顺序由 daemon coordinator 保证

把原先跨 GUI/Telegram client 的关键顺序收敛到一个进程：

```text
Telegram fetch
→ JSON atomic write success
→ local checkpoint update success
→ optional Telegram read acknowledgement
```

因此 daemon 的 `ExportCoordinator` 必须负责：

1. 调用 `export_group()`；
2. 确认 final JSON 原子替换成功；
3. 更新 `local_state.json` checkpoint；
4. 只有此前全部成功且该群明确 Option B ON 时才 ack read；
5. read ack 失败不删除 JSON，只单独记录状态。

这比把 read ack 作为一个可随意调用的公共 IPC 方法更安全。

## 6. 普通 RPC 模型

短操作采用一请求一连接：

```text
open Named Pipe
→ auth handshake
→ send one request JSON frame
→ receive one response JSON frame
→ close
```

这样不需要第一版实现复杂的多路复用长连接。

头像等并发小请求可开多个短连接；daemon 内统一限流。

潜在大结果（chat catalogue / message search）必须提供服务端 limit / pagination，而不是无限制单 frame。

建议单 frame hard cap：**8 MiB**。超过返回结构化 `IPC_RESPONSE_TOO_LARGE`，客户端必须改用分页/更小 limit，不允许静默截断。

## 7. IPC 协议 v1

协议版本独立于产品版本：

```text
protocol = "tgipc/1"
```

请求：

```json
{
  "protocol":"tgipc/1",
  "request_id":"uuid",
  "client":{
    "kind":"gui",
    "app_version":"0.2.0"
  },
  "method":"chats.list",
  "params":{},
  "deadline_ms":30000
}
```

成功：

```json
{
  "protocol":"tgipc/1",
  "request_id":"uuid",
  "ok":true,
  "result":{}
}
```

失败：

```json
{
  "protocol":"tgipc/1",
  "request_id":"uuid",
  "ok":false,
  "error":{
    "code":"CHAT_NOT_FOUND",
    "message":"...",
    "details":{}
  }
}
```

要求：

- daemon 不返回 traceback；
- 未知字段可忽略，未知 method 必须明确拒绝；
- request_id 只用于关联，不包含用户数据；
- 日志可记 request_id/method/duration/status，不记 message body；
- `tgctl --json` 对外继续映射现有 v0.1.9 JSON envelope，不要求用户/Codex感知 `tgipc/1`。

## 8. Capability / 版本握手

第一条诊断 RPC：

```text
system.hello
```

返回：

```json
{
  "protocol":"tgipc/1",
  "daemon_app_version":"0.2.0",
  "pid":1234,
  "capabilities":[
    "status",
    "chats.list",
    "messages.search",
    "messages.get",
    "forward",
    "send",
    "export.jobs"
  ]
}
```

升级规则：

- protocol major 不兼容：拒绝调用；
- protocol major 相同但 daemon 缺少所需 capability：返回 `DAEMON_UPGRADE_REQUIRED`；
- 新客户端不得在旧 daemon 上偷偷回退成 direct SQLiteSession；
- 若 daemon 无活跃 GUI lease/job，可请求 graceful shutdown 后由新版本重启；
- 有活跃客户端/job 时不强杀，提示用户完成/关闭后升级。

## 9. 并发策略

目标不是让所有 Telegram 操作无限并行，而是让多个前端安全共享一个 owner。

建议：

- daemon 接收多个 IPC 请求；
- read operations 可有限并发，例如全局 semaphore 8；
- avatar requests 可继续受限并发；
- Telegram write operations 使用独立 `asyncio.Lock` 串行化；
- auth state transitions 串行化；
- export jobs 第一版按批次顺序执行，避免同时对多个大群拉历史造成 FloodWait/资源竞争；
- tgctl 的轻量 read 可以与 GUI export 共存，但 daemon 可按 semaphore/priority 控制。

不能因为 IPC 并发而移除 Telegram FloodWait 保护。

## 10. tgctl 迁移

对用户保持：

```text
tgctl status
tgctl chats list
tgctl messages search
tgctl messages get
tgctl forward
tgctl send
```

命令参数、JSON envelope、稳定错误码、exit code 尽量保持 v0.1.9 兼容。

内部从：

```text
tgctl → TelegramService → TelegramClient
```

改为：

```text
tgctl → IPCClient → daemon → TelegramService → TelegramClient
```

### 10.1 写安全必须下沉到 daemon 再验证

不能只依赖 tgctl argparse 层。

future MCP 可能直接调用 daemon，因此 daemon 对 write RPC 必须再次验证：

- `dry_run`；
- forward default 20 / explicit 200 hard cap；
- destination resolution；
- AMBIGUOUS_CHAT；
- allowed message/media scope；
- FloodWait stop；
- no-body logging。

CLI 层继续做早期 validation，但 server 才是最终安全边界。

## 11. GUI 迁移

GUI 保持 qasync 单事件循环，但不再让 Telethon 进入 GUI 进程。

新增 async `TelegramProxy`，尽量提供与 GUI 当前依赖相同的方法：

```text
account_info
list_groups
resolve_group
group_avatar_bytes
export job methods
login/auth methods（仅 GUI）
close client lease
```

底层 blocking Named Pipe 调用使用 `asyncio.to_thread()` 或专用轻量 worker，不能阻塞 Qt/qasync UI loop，也不能重新引入 nested `QDialog.exec()`。

GUI 关闭只释放它自己的 daemon client lease，不直接关闭 Telegram Session；daemon 根据 idle policy 决定是否退出。

## 12. 首次登录 / 未授权 Session

新架构仍必须支持全新安装，而不仅是已登录升级。

Daemon 可在没有 TelegramService 的 bootstrap 状态先启动 IPC。

GUI 登录流程：

```text
GUI 启动 daemon bootstrap
→ GUI 提供 API credentials（沿用现有本地 credential store 语义）
→ daemon initialize TelegramService
→ GUI 通过 auth RPC request code
→ submit code
→ 如需要 submit 2FA password
→ Session 仍由 daemon 创建/持有
```

安全要求：

- phone / api_hash / OTP / 2FA 只在 authenticated local pipe 必要请求中短暂存在；
- 不写 IPC debug dump；
- 不进入普通日志；
- tgctl 仍没有交互式登录能力，未授权仍返回 `NOT_AUTHORIZED` 并提示用 GUI 登录。

## 13. Daemon crash / restart 语义

### 13.1 Read request

如果 daemon 在 read request 中崩溃：

- IPC client 可重新 `ensure_running()`；
- read-only 请求允许自动重试最多一次；
- 仍须遵守原来的 limit/deadline。

### 13.2 Write request

**写请求禁止因为 IPC 断开而自动重试。**

原因：

```text
daemon 已把 forward/send 交给 Telegram
→ Telegram 可能已经成功
→ daemon 在返回 response 前崩溃
```

此时客户端无法可靠判断是否已经写入。自动重试可能造成重复发送/重复转发。

应返回新的结构化状态，例如：

```text
WRITE_OUTCOME_UNKNOWN
```

并要求用户/Codex先检查目标聊天，再决定是否重试。

这是 daemon 架构必须新增的分布式故障安全边界。

## 14. client lease 与 idle shutdown

GUI 是长生命周期 client，建议：

```text
client.register
→ lease_id
→ 每 20~30 秒 heartbeat
→ GUI close 时 client.release
```

Daemon：

- heartbeat 超时的 lease 自动清理；
- 有 lease / active job / active request 时不 idle shutdown；
- 无 lease、无 job、无请求达到 idle timeout 后 graceful disconnect Telethon 并退出。

`tgctl` 是 one-shot 客户端，不需要长期 lease。

## 15. Daemon 启动方式与打包

设计优先保持用户现有下载体验，不强迫用户额外维护 Windows Service。

第一实施版建议使用 **self-hosted daemon mode**：

- `TGExporter.exe` 与 `tgctl.exe` 打包时都包含 daemon 模块；
- 当 client 发现 daemon 不存在时，以隐藏内部参数启动一个后台 daemon mode；
- daemon singleton lock 保证最终只有一个 owner；
- 用户不需要手工启动 daemon。

优点：

- 不要求单文件 GUI 用户再单独下载第三个 EXE；
- standalone tgctl 也能独立自举 daemon；
- 保持 Release 资产使用习惯。

如果 PyInstaller self-spawn 在实现期暴露不可接受问题，再切换为正式 `tg-daemon.exe` 第三资产；但不能为了打包方便退回多个 Session owner。

## 16. Error model

继续保留现有业务错误：

```text
NOT_AUTHORIZED
CHAT_NOT_FOUND
AMBIGUOUS_CHAT
MESSAGE_NOT_FOUND
FLOOD_WAIT
WRITE_FAILED
INVALID_ARGUMENT
```

`SESSION_BUSY` 只主要用于：

- 旧版本进程仍直接占用 Session；
- daemon 无法取得 SessionLease。

正常新架构 GUI + tgctl 并发不应再出现 `SESSION_BUSY`。

新增 IPC/lifecycle 错误建议：

```text
DAEMON_START_FAILED
DAEMON_UNAVAILABLE
DAEMON_UPGRADE_REQUIRED
IPC_PROTOCOL_ERROR
IPC_RESPONSE_TOO_LARGE
IPC_TIMEOUT
WRITE_OUTCOME_UNKNOWN
```

这些必须稳定映射到 tgctl 非零 exit code，但不输出 traceback。

## 17. 日志与隐私

Daemon log 继续写既有本地 logs 目录，可增加：

```text
request_id
client_kind
method
duration_ms
chat_id/message_id/count
result/error_code
job_id/progress count
```

禁止：

```text
message body
api_hash
phone
OTP
2FA
Session contents
IPC auth secret
avatar bytes/base64
完整 request/response JSON dump
```

尤其禁止为了“调 IPC”直接 `logger.debug(request)`，因为 search/get/send params 可能含正文。

## 18. 测试计划

### 18.1 单元测试

- protocol envelope encode/decode；
- reject pickle/object path；
- frame size cap；
- unknown method；
- invalid params；
- auth secret lifecycle；
- daemon singleton lock；
- client lease timeout；
- capability/version negotiation；
- write policy server-side revalidation；
- log redaction；
- read retry once；
- write disconnect => `WRITE_OUTCOME_UNKNOWN`，绝不 auto retry。

### 18.2 Windows IPC integration（无 Telegram Secret）

使用 fake Telegram backend：

- 起真实 AF_PIPE daemon；
- GUI-style client + tgctl-style client 同时连接；
- 并发 reads；
- write serialization；
- export fake job progress/result；
- kill daemon 后 read auto-recover；
- kill daemon during fake write 后确认不重试；
- incompatible protocol/version；
- stale client lease cleanup。

### 18.3 现有回归

必须继续跑：

- pytest 全量；
- GUI import/qasync regression；
- current unread frozen snapshot；
- Option B success ordering；
- migration historical export；
- Export Category/output path；
- tgctl JSON/ambiguous/batch/FloodWait tests。

### 18.4 PyInstaller smoke

至少验证：

```text
TGExporter packaged launch
TGExporter daemon bootstrap path
tgctl packaged launch
tgctl daemon bootstrap path
GUI + tgctl concurrent IPC smoke with fake/no-auth backend
```

CI 不放真实 Telegram credentials。

### 18.5 真人 E2E

发布候选仅在用户本机验证：

1. 老 v0.1.9 Session 无迁移/无重新登录；
2. GUI 开着时 `tgctl status/chats/search` 正常，不再 SESSION_BUSY；
3. GUI export 同时 tgctl read；
4. forward/send dry-run；
5. Saved Messages 单条真实 forward/send；
6. daemon crash 后 read 自动恢复；
7. 写操作故障不自动重复；
8. GUI 退出、idle 后 daemon 自动退出；
9. 再次调用自动启动；
10. 日志无 secret/body。

## 19. 分阶段实施计划

### Phase A — transport / protocol skeleton

- `ipc_protocol.py`
- `ipc_transport.py`
- `daemon_server.py` fake backend
- `ipc_client.py`
- Windows AF_PIPE integration tests

此阶段不迁 Telegram 生产调用。

### Phase B — daemon owns TelegramService, 先迁 tgctl

- daemon 初始化现有 TelegramService；
- tgctl 的 status/chats/search/get → IPC；
- forward/send → IPC；
- write safety 下沉 server；
- v0.1.9 对外 CLI 协议保持兼容。

此阶段可先在开发分支运行，不急着发布。

### Phase C — GUI read/auth/avatar 迁移

- GUI service reference 换 `TelegramProxy`；
- list groups / account / avatar / login 经 IPC；
- 确认 qasync 不阻塞。

### Phase D — GUI export job 迁移

- `ExportCoordinator` 进入 daemon；
- daemon 执行 Telegram fetch + atomic JSON + checkpoint + optional read ack；
- GUI 只提交 plan / 读 progress/result；
- 确保 migration/date-range/current-unread 行为不变。

完成这一阶段后，GUI 与 tgctl 才真正都不再直接打开 Session。

### Phase E — lifecycle / crash recovery / packaging

- auto-start；
- singleton；
- client lease / idle shutdown；
- version negotiation；
- packaged self-daemon smoke；
- upgrade from v0.1.9 real Session。

### Phase F — Release candidate / user E2E

所有 CI 全绿后再做 v0.2.0 candidate；真实 Telegram write 仍只由用户本机 E2E，优先 Saved Messages。

## 20. Release gate

不能因为“多数功能已经 IPC 化”就发布。

v0.2.0 的硬 gate：

- GUI 与 tgctl 都不再直接创建生产 TelegramClient；
- 只有 daemon 获得 SessionLease；
- GUI + tgctl 并发真实 read 不出现 SESSION_BUSY；
- GUI export 仍完整保持现有输出/Option B/migration 语义；
- tgctl JSON/exit code 基本兼容 v0.1.9；
- write safety 在 daemon 端也验证；
- write transport failure 不自动重试；
- daemon crash 可恢复；
- 无 TCP/Web server；
- 无真实 Telegram Secret 进入 CI；
- Windows packaged smoke 全绿；
- HANDOFF 明确 CI 与真人 E2E 边界。

## 21. 后续 MCP 如何接入

当本设计稳定以后，MCP 不应该再碰 Telethon/Session，只新增一个薄 client：

```text
MCP tool schema
→ same IPCClient
→ same daemon policy
→ same TelegramService
```

因此未来 MCP 不会产生第三套 Telegram 逻辑，也不会重新引入 SQLiteSession ownership 问题。

MCP 的 write confirmation policy 需要单独设计，不能因为 daemon 已经支持 send/forward 就自动授权 Agent 无确认写入。
