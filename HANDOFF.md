# HANDOFF.md

> 当前开发交接快照。任何 Agent 接手前先读 `AGENTS.md`，再读本文件。

更新时间：2026-08-29

## 1. 当前正式版本

- 正式版：**TG Exporter v0.1.9**
- Release：`https://github.com/3ll3-3ll3/tg-exporter/releases/tag/v0.1.9`
- merge commit：`22014f5999867e5d0b0e6c1e46320320fc974cd0`
- Release workflow：`33258806323` success
- 正式 SHA-256：
  - GUI one-file `b2e349a7165de106f3f338df1fa44061b152ad70b0c1d71370c81758b98529cf`
  - Portable `42af909157a624d5bc58fddb60b4f4bf6a520d9fe017a7ba115dbd2ea84f3d22`
  - `tgctl.exe` `028fee5cec1ec6d28edee5e51a605a1560bca9188636d10dec37abc0eb35de53`

v0.1.8 GUI/category/migrated-supergroup/session compatibility 已由用户真人验证通过。v0.1.9 tgctl 真人 E2E 仍由用户本机测试中；不要把 CI/mock 当真人结果。

## 2. 已接受的下一阶段：v0.2.0 single daemon + local IPC

用户已授权直接开始实现。目标解决 v0.1.9 `SESSION_BUSY`，但不是让 Telegram 操作无限并发。

```text
TG daemon（唯一 Session/Telethon owner）
├─ TG Exporter GUI IPC client
├─ tgctl IPC client
└─ future MCP IPC client（本版不实现）
```

详细设计：`docs/DAEMON_IPC_DESIGN.md`。
长期决策：`docs/DECISIONS.md` D-026 ~ D-032。

## 3. 用户已经确认的桌面体验

- **1B**：关闭 GUI 时，正在导出的 job 继续后台完成。
- **2A**：GUI 没开时，Codex/tgctl 可自动唤醒 daemon。
- **3B**：导出期间 tgctl 的 Telegram 搜索/读取等待导出结束，不与导出并发。
- **4B**：导出期间真正 send/forward 禁止执行，返回 `EXPORT_IN_PROGRESS`；不得排队后偷偷发送。
- **5B**：GUI 崩溃后 daemon/job 继续；重开 GUI 恢复看到 job 进度/最近结果。
- **6B**：daemon 显示 Windows 托盘图标，可看状态、打开 TG Exporter、请求退出。
- **7A**：phone/OTP/2FA 交互仍只在 GUI；tgctl/Codex 不登录。
- **8B**：无 GUI lease、无 job、无请求/排队 read 后约 10 分钟 idle exit；下次自动唤醒。

## 4. v0.2.0 核心架构不变量

1. 仍只有一份 `%APPDATA%\TelegramMultiChatExporter\telegram.session`，不复制 Session。
2. GUI/tgctl 完成迁移后不得直接创建 TelegramClient，也不得在 daemon 失败时回退 direct SQLiteSession。
3. 现有 `SessionLease` 保留，由 daemon 获取；用于兼容阻止旧 v0.1.9 进程同时打开 Session。
4. IPC 首选 Windows Named Pipe / `AF_PIPE`，只传 UTF-8 JSON bytes，禁止 pickle object transport；不开 TCP/HTTP。
5. IPC 使用本地随机 identity/auth secret，secret 不日志、不 stdout、不 Git。
6. GUI 导出 job 必须 daemon-side 执行并直接原子写 JSON，不能把大量正文通过 Pipe 发回 GUI。
7. `JSON success → checkpoint → optional read ack` 继续由 daemon coordinator 保证。
8. export 是独占 Telegram job；纯本地 status/job/heartbeat RPC 不受阻塞。
9. 真 write 在 export 活跃时拒绝；无 export 时仍保留 dry-run、20/200 cap、AMBIGUOUS_CHAT、FloodWait、媒体限制、no-body logging。
10. write 请求传输中断绝不自动 retry，返回 `WRITE_OUTCOME_UNKNOWN`。
11. daemon 不做 Windows Service/开机自启/24x7 listener/自动规则/MCP。

## 5. 预计模块

```text
src/telegram_exporter/
├─ daemon_main.py
├─ daemon_server.py
├─ daemon_manager.py
├─ daemon_tray.py
├─ operation_coordinator.py
├─ ipc_identity.py
├─ ipc_protocol.py
├─ ipc_transport.py
├─ ipc_client.py
├─ telegram_proxy.py
└─ export_coordinator.py
```

`telegram_service.py` / `exporter.py` 继续作为 daemon-side Core。

## 6. 实施顺序

### Phase A — IPC foundation
identity/auth、AF_PIPE JSON bytes、protocol validation、daemon singleton、ensure_running、fake backend tests。此阶段不碰真实 Telegram。

### Phase B — daemon owns Telegram + tgctl
TelegramService 移入 daemon；tgctl 全部走 IPC；保持 v0.1.9 CLI JSON/exit code 兼容；实现 export/read/write 调度安全层与 write unknown outcome。

### Phase C — GUI auth/read/avatar + tray
GUI 登录 RPC、catalogue/avatar IPC、GUI lease/heartbeat、托盘 status/open/exit-after-export；GUI 不再创建 TelegramClient。

### Phase D — GUI export jobs
ExportCoordinator、daemon-side checkpoint/read ack、job progress/result、GUI close/crash 后继续、重开恢复。

### Phase E — lifecycle/packaging
idle 10min、autostart/recovery、safe job metadata、PyInstaller `tg-daemon.exe`、packaged smoke tests。

### Phase F — v0.2.0 Release gate
Windows CI 全绿 + 用户真人 E2E 后发布。

## 7. 仍保持的历史规则

- 输出：`总目录 / Export Category / 群组 / YYYY-MM-DD_HH-mm-ss.json`；历史 JSON 不合并。
- 聊天消息不下载媒体；头像只是 UI cache。
- migrated Basic Group 只显示当前 Supergroup；date-range 可读取 legacy+current。
- current unread frozen snapshot。
- Option B 默认 OFF：JSON success → checkpoint → optional read ack。
- Qt/qasync 不重新引入 nested blocking modal。
- 日志严禁 api_hash/phone/OTP/2FA/Session/message body。

## 8. 当前分支/PR 状态

设计 PR：`#17 docs: design single Telegram daemon + local IPC`。
用户已经确认体验并要求“直接开始工作”。设计文档可以合并为实施基线，然后从最新 main 新建 v0.2.0 功能分支。

在 v0.2.0 正式 Release 前，**v0.1.9 仍是正式可用版本**，不得覆盖或伪称新架构已发布。
