# HANDOFF.md

> 这是本仓库的**当前开发交接快照**。任何 Agent 接手前先读 `AGENTS.md`，再读本文件。完成用户可见功能、关键修复或 Release 后必须更新本文件。

更新时间：2026-08-28

## 1. 当前版本状态

### 最新正式 Release

- **v0.1.4**
- Release: `https://github.com/3ll3-3ll3/telegram-multi-chat-exporter/releases/tag/v0.1.4`
- Release target commit: `d803eb5df2d9f4b6322071442d421b9c7a541c66`
- 正式分发：GitHub Releases（不是 Actions Artifact）

### main 比 v0.1.4 多出的未发布修复

当前 `main` 已包含退出清理 hotfix：

- `659298e88cc5a9449b3055c3febb1b3737820e71` — 兼容 Telethon `disconnect()` 返回 awaitable 或直接完成的两种情况。
- `3d3797cb73b24fc39a0765fc88c2af78aedaf892` — shutdown 清理错误只记日志，不再升级成 PyInstaller 致命异常框。

Windows CI run `33146614769` 已全部通过：

- pytest
- GUI import check
- Windows EXE build
- packaged EXE smoke-test
- artifact upload

**但这两个修复在写本交接时尚未发布成新的 GitHub Release。** 下一次二进制 Release 应至少包含它们，建议版本 `v0.1.5`（若期间还有其他修复，可一起发布）。

## 2. 用户已实际验证过什么

已由真实账号验证：

- Telegram API 登录成功。
- Windows 系统代理检测可识别 Clash `http://127.0.0.1:7890`。
- Telethon transport 通过该代理成功连接 Telegram。
- 账号 Session 可保存并复用。

曾由用户日志定位并修复：

1. **系统代理未被 Telethon 自动继承** → v0.1.2 起显式读取 Windows 系统代理。
2. **qasync nested modal dialog 重入** → v0.1.3 改为非阻塞 dialog await 模式。
3. **关闭程序时 `await None`** → main 已修，尚待 Release；见上一节。

尚不能仅凭 CI 宣称已完成的真实账号 E2E：

- 五个以上群的混合模式完整批次导出。
- `导出后标已读` 对手机/桌面端 read marker 的真实同步验证。
- 与 Telegram Desktop 同一群/同一时间窗口的 JSON differential test。

## 3. v0.1.4 已有用户可见能力

- Windows PySide6 GUI。
- Telegram 首次手机号 / code / 2FA 登录。
- 本地 Session 复用。
- Windows 系统代理自动检测与 Telethon 显式代理。
- 本地轮转日志。
- API 设置、重置登录、打开日志目录。
- 完整账号群组只作为后台 catalogue。
- `选择群组` 搜索/勾选；主面板只显示固定工作群。
- 已选工作群跨启动持久化。
- 每群独立模式：
  - 指定时间范围；
  - 当前未读；
  - 上次导出以后。
- 当前未读使用刷新时冻结快照。
- Option B：每群独立 `导出后标已读`，默认 OFF，仅未读模式可用。
- 每个群独立 `result.json`。
- 每次运行独立批次目录。
- 文本/caption-only；不下载媒体。
- Telegram Desktop 风格的核心 JSON 字段。
- one-file EXE + portable ZIP + SHA256SUMS 的 Release 流程。

## 4. 关键产品不变量

不要改变以下方向，除非用户明确要求：

- 不是累计归档库；不建设 master DB。
- 历史批次不合并、不回写。
- 不下载照片/视频/语音/文件/贴纸。
- JSON 是权威数据源。
- 每群规则独立。
- 主工作区只显示用户选中的少量群。
- 默认导出不改变 Telegram 已读状态。
- read acknowledgement 只能在用户为该群明确启用 `导出后标已读` 后发送。
- 导出 JSON 成功后才能标已读。
- GUI-first，最终用户不应依赖 CLI。

更完整规则见 `AGENTS.md`。

## 5. 当前代码结构（重要）

主要入口：

- `launcher.py`：PyInstaller 入口；`--smoke-test` 只做导入验证。
- `src/telegram_exporter/main.py`：QApplication + qasync event loop；当前导入 `focused_gui.MainWindow`。

GUI 有历史演进层次：

- `gui.py`：早期基础 GUI/通用实现。
- `gui_async.py`：在基础 GUI 上增加 qasync-safe 非阻塞 dialog 行为。
- `focused_gui.py`：当前实际主界面；在 qasync-safe 层上加入 focused workspace、未读快照和 Option B read policy。
- `group_selector.py`：完整群目录的搜索/选择弹窗。

**不要误把 `gui.py` 当当前最终 MainWindow。** 实际启动链是：

```text
launcher.py
→ telegram_exporter.main
→ telegram_exporter.focused_gui.MainWindow
```

后续可以考虑合并 GUI 层次降低技术债，但重构前必须保留 qasync-safe 行为并增加回归测试。

核心服务：

- `telegram_service.py`：Telethon client、登录、dialog catalogue、代理连接、disconnect。
- `proxy.py`：Windows 系统代理解析/检测。
- `exporter.py`：按计划读取 Telegram 消息并写每群 `result.json`。
- `read_state.py`：显式 read acknowledgement 逻辑。
- `desktop_json.py`：Telegram Desktop 风格 JSON serializer。
- `models.py`：GroupInfo / GroupExportPlan / ExportMode。
- `storage.py`：本地 settings/state JSON 与 atomic write。
- `paths.py`：`%APPDATA%\TelegramMultiChatExporter` 路径。
- `logging_setup.py` / `diagnostics.py`：日志与用户友好错误。

## 6. 当前 JSON 兼容缺口

详见 `docs/JSON_COMPATIBILITY.md`。当前最重要的技术债：

1. `text_entities` 目前把整段文字作为一个 `plain` entity；未映射 bold/link/mention/code 等 Telegram entities。
2. chat `type` 仍需要做到真实判断，避免硬编码/错误分类。
3. 顶层 chat `id` 需要与 Telegram Desktop 的 ID 规则做实测差异验证；Telethon marked peer id 不能简单等同官方导出 id。
4. 文本路径目前历史实现使用 `.strip()`，会改变首尾 whitespace；追求纯文本兼容时应改为原样保留，同时仍能判断“无文本媒体”。
5. service message / forward metadata 尚未完整映射。
6. media metadata 大部分不支持是**产品刻意选择**，不要因为兼容度目标擅自开始下载媒体。

## 7. 当前可靠性技术债

优先级建议：

### P0/P1

- 把 main 上退出 hotfix 发布为新正式 Release，并由用户验证“关闭不再弹 Unhandled exception”。
- 真实账号测试 `导出后标已读`：确认只推进到刷新时冻结的 `latest_message_id`。

### P1

- `result.json` 改成临时文件 + atomic replace，避免写到一半异常留下半文件。
- 处理两个群名清洗后目录名相同的 collision（建议稳定附加 chat id）。
- 修正/验证 Telegram Desktop chat type 和 top-level id。
- 原样保存文字 whitespace。

### P2

- rich text entity mapping。
- forward metadata / service message 的纯文本兼容策略。
- 每行实时消息进度、失败群一键重试。
- GUI 层次收敛（`gui.py` / `gui_async.py` / `focused_gui.py`），但不可牺牲 qasync 安全。

## 8. 未读与已读语义（接手前必须理解）

刷新 catalogue 时每个群保存：

- `unread_count`
- `read_inbox_max_id`
- `latest_message_id`

本次未读窗口固定为：

```text
read_inbox_max_id < id <= latest_message_id
```

`导出后标已读`：

```text
write result.json success
→ local checkpoint
→ send_read_acknowledge(max_id=latest_message_id)
```

注意 Telegram 的 read marker 是按 ID 的，所以该范围中的媒体/系统消息即使没进入纯文本 JSON，也可能随 max_id 一起变成已读。这是预期副作用，UI 必须告知用户。

## 9. 本地文件与敏感信息

默认目录：

```text
%APPDATA%\TelegramMultiChatExporter\
```

典型文件：

```text
api_credentials.json
telegram.session
local_state.json
settings.json
logs\app.log
```

仓库和日志禁止出现 api_hash、手机号、验证码、2FA、Session 内容、聊天正文。

## 10. 版本与发布

- `VERSION` 和 `pyproject.toml` version 必须一致。
- 正式 Release workflow 只应在准备好发布时触发。
- 用户下载入口是 GitHub Releases。
- 发布前必须检查 `docs/RELEASE_PROCESS.md`。
- 发布后新增/更新 `docs/releases/vX.Y.Z.md`，并更新本文件顶部“当前版本状态”。

## 11. 当前不做的事情

除非用户重新提出：

- 不继续投入 360/杀软误报、代码签名申请等工作。
- 不做完整 Telegram 媒体备份。
- 不做云端消息数据库。
- 不自动绕过安全软件。

## 12. 下一 Agent 最推荐的起手动作

如果用户没有提出新的功能，优先顺序：

1. 确认 main 的 shutdown hotfix CI 仍为 green。
2. 发 `v0.1.5`（或包含后续修复的新版本）。
3. 让用户实测关闭窗口。
4. 用一个小群做“当前未读 + 导出后标已读”真实 E2E。
5. 取同一群同一时间窗的 Telegram Desktop `result.json` 做 differential comparison。
6. 再做 JSON 兼容和 atomic output 等可靠性改进。
