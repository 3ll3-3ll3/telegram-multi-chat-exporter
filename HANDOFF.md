# HANDOFF.md

> 当前开发交接快照。任何 Agent 接手前先读 `AGENTS.md`，再读本文件。

更新时间：2026-08-30

## 1. 当前正式版本

当前正式版仍是 **TG Exporter v0.1.9**，直到 v0.1.10 hotfix PR 合并并完成正式 Release workflow 才改变。

- Release：`https://github.com/3ll3-3ll3/tg-exporter/releases/tag/v0.1.9`
- PR：`#16`
- release/merge target：`22014f5999867e5d0b0e6c1e46320320fc974cd0`
- Release workflow：`33258806323`，success

v0.1.9 正式资产 SHA-256：

- `TGExporter-v0.1.9-windows-x64.exe`
  - `b2e349a7165de106f3f338df1fa44061b152ad70b0c1d71370c81758b98529cf`
- `TGExporter-v0.1.9-windows-x64-portable.zip`
  - `42af909157a624d5bc58fddb60b4f4bf6a520d9fe017a7ba115dbd2ea84f3d22`
- `tgctl.exe`
  - `028fee5cec1ec6d28edee5e51a605a1560bca9188636d10dec37abc0eb35de53`

## 2. v0.1.8 真人验证

用户已明确确认 v0.1.8 相关体验“都验证通过”，包括：

- Export Category 创建/保存/自动建目录；
- `output/category/group/timestamp.json` 长期目录结构；
- 群分类分配与重启持久化；
- migrated legacy Basic Group catalogue collapse；
- 当前 Supergroup 不消失、不退群、不被修改；
- DATE_RANGE 可包含升级前 legacy + 当前 Supergroup 历史；
- 旧 Session/settings 升级复用。

不要因为后续某次测试环境暂时没有自定义分类，就把上述已完成的历史真人验证改写成“未验证”。

## 3. v0.1.9 真人 Windows E2E（2026-08-30）

用户使用正式 v0.1.9 二进制完成了较完整的本地验收。测试期间没有修改代码/提交 Git/上传数据，真实 Telegram 写操作只针对 Saved Messages。

已真人确认 PASS：

- 正式 GUI/tgctl SHA-256 与 Release 一致；
- 本地 AppData 已先备份；
- GUI 正常启动/退出；
- GUI 与 tgctl 均直接复用已有 Telegram Session，无 phone/OTP/2FA；
- GUI 小范围 current-unread 导出成功并产生合法 JSON；
- `tgctl --help`；
- `status --json`；
- `chats list`；
- chats search/limit；
- 真实 Telegram Chat Folder 筛选；
- `messages search` + since/until；
- `messages get`；
- 不存在消息 -> `MESSAGE_NOT_FOUND` + exit 4；
- 真实同名会话 -> `AMBIGUOUS_CHAT` + exit 5 + 候选，不 first-match；
- forward dry-run CLI 结果；
- real forward CLI 调用到 Saved Messages；
- send dry-run CLI 结果；
- real send CLI 调用到 Saved Messages；
- 默认 20 条 forward guard；
- 200 条 allow-large hard cap；
- FloodWait 代码/既有 mock 测试映射正确且没有 retry storm；
- 日志中测试正文/api_hash/手机号/OTP/2FA 值匹配为 0；
- 正式打包 GUI/tgctl 在真实读取、导出、send、forward 流程未崩溃。

仍需人工/条件补充：

- migrated Supergroup 的某一具体旧/新 peer 映射最好继续肉眼确认；
- Saved Messages 中 dry-run 无新增、real forward 显示 Telegram 正常转发来源、real send 无重复/无意外格式解析仍属于 UI 视觉确认项；
- `tgctl -> GUI` 反向 Session busy 真人场景因命令执行太快未强行制造；
- 不要为了真人 E2E 故意触发 FloodWait。

## 4. v0.1.9 发现的明确 packaged CLI Bug

真人验收发现：GUI 持有 Session 时运行：

```text
tgctl.exe status --json
```

预期契约：

```text
JSON error.code = SESSION_BUSY
native process exit code = 8
```

v0.1.9 用户机器观察到退出码为 1。随后在独立 Windows GitHub Actions 上使用真实 OS `SessionLease` + 正式 one-file `tgctl.exe` 复现并定位根因。

**根因不是 `_exit_code()` 映射错误。** 源码本来就正确把 `SESSION_BUSY` 映射为 8。

真实根因：

```text
SessionBusyError 正确抛出
→ tgctl 进入 except SessionBusyError
→ 准备输出中文 JSON
→ 打包进程 stdout 在测试环境使用 cp1252
→ ensure_ascii=False 的中文 error message 触发 UnicodeEncodeError
→ 错误处理本身再次异常
→ PyInstaller 顶层退出 1
```

诊断 CI：

- run `33286735820`
- Python tests：50 passed
- GUI build：success
- tgctl build：success
- packaged regression 捕获：exit 1 / stdout empty / stderr 明确 `UnicodeEncodeError`。

因此 v0.1.9 Session OS lock 本身没有失效；问题是 packaged console encoding 打断了 JSON/exit-code 契约。

## 5. v0.1.10 hotfix

分支：

```text
hotfix/session-busy-exit-v0.1.10
```

范围必须保持最小，不混入 daemon/MCP 改造。

已实现：

- `tgctl` 启动时显式将 stdout 配成 UTF-8 strict；
- stderr 配成 UTF-8 + defensive `backslashreplace`；
- JSON 继续 `ensure_ascii=False`，但不再受 legacy Windows code page 限制；
- 新增 source-level `SESSION_BUSY -> exit 8` 测试；
- 新增模拟 cp1252 stream 的 UTF-8 重配置测试；
- 新增真实 OS Session lock holder 测试 helper；
- Windows CI 构建真实 one-file tgctl 后，用 `.NET Process` 捕获 native stdout/stderr/ExitCode，强制断言 `SESSION_BUSY` + exit 8。

修复验证 CI：

- run `33286890846`
- pytest：success
- GUI/tgctl import：success
- GUI build：success
- tgctl build：success
- packaged SESSION_BUSY JSON/exit-code contract：success
- packaged smoke：success
- artifact upload：success

v0.1.10 candidate 版本文件/Release Notes 已准备；正式 Release workflow 也增加 standalone + portable tgctl 的同一 packaged contract gate。

**在 PR merge + Release workflow success 前，仍不得把 v0.1.10 写成正式版。**

## 6. v0.1.9/v0.1.10 tgctl 安全边界

命令：

```text
tgctl status
tgctl chats list
tgctl messages search
tgctl messages get
tgctl forward
tgctl send
```

长期规则：

- CLI 复用 `%APPDATA%\TelegramMultiChatExporter\api_credentials.json` 与 `telegram.session`；
- CLI 不实现 phone/OTP/2FA 登录；
- read commands 不偷偷改变 read marker；
- `forward` 必须使用 Telegram true forward；
- `send` 只做纯文本，`parse_mode=None`；
- forward/send 均保留 `--dry-run`；
- 默认 forward <=20；显式 allow-large 后 hard cap 200；
- 同名 chat -> `AMBIGUOUS_CHAT`；
- FloodWait 返回结构化等待秒数，不 retry storm；
- write log 不记录正文；
- JSON stdout 不混普通 logging；
- v0.1.x GUI/tgctl 仍使用 SessionLease 互斥，同一 SQLiteSession 不并发打开。

## 7. parallel v0.2.0 single-daemon 主线

用户已经确认下一代桌面体验，并明确要求开始实施，但它与 v0.1.10 hotfix 独立推进。

设计 PR：

- Draft PR #17 `docs: design single Telegram daemon + local IPC`
- 分支：`design/single-daemon-ipc-v1`

实现分支：

```text
codex/single-daemon-v0.2.0
```

用户确认 UX：

- 关 GUI 时正在导出的 job 后台继续；
- GUI 未打开时 tgctl/Codex 可按需唤醒 daemon；
- 导出期间 read/search 等待导出完成；
- 导出期间真实 send/forward 直接拒绝，不排队后偷偷发送；
- GUI 崩溃/关闭不终止后台 export，重开可恢复进度/结果；
- daemon 有 Windows tray icon；
- phone/OTP/2FA 仍只在 GUI；
- 无 GUI/job/request 后约 10 分钟 idle exit，下次再自动唤醒。

目标架构：

```text
single local TG daemon owns TelegramService / Telethon / telegram.session
├─ TG Exporter GUI IPC client
├─ tgctl IPC client
└─ future MCP IPC client（v0.2.0 不实现 MCP）
```

v0.2.0 仍是开发状态，**没有正式 Release**。不要把它与 v0.1.10 hotfix 的正式发布状态混淆。

v0.1.10 的 UTF-8 CLI 输出修复及 packaged regression test 后续应 forward-port 到 v0.2.0 分支，因为 daemon 架构下的 tgctl 仍然需要稳定 UTF-8 JSON stdout。

## 8. Release discipline

默认流程继续是：

```text
latest main
→ feature/hotfix branch
→ pytest + Windows packaged tests
→ PR
→ PR CI green
→ squash merge
→ user-visible binary change uses `release: vX.Y.Z`
→ formal Release workflow
→ verify Release target/assets/SHA256
→ update HANDOFF with formal state
```

真实 Telegram 写操作 CI 继续只能使用 mock/isolated local lock tests，不得把用户 Telegram credential 放入 GitHub Actions。
