# HANDOFF.md

> 这是本仓库的**当前开发交接快照**。任何 Agent 接手前先读 `AGENTS.md`，再读本文件。完成用户可见功能、关键修复或 Release 后必须更新本文件。

更新时间：2026-08-28

## 1. 当前版本状态

### 最新正式 Release

- 当前已发布：**TG Exporter v0.1.6**
- Release: `https://github.com/3ll3-3ll3/telegram-multi-chat-exporter/releases/tag/v0.1.6`
- Release target commit: `531c31495cf10770943b45d2850e2b5ce71c6553`
- Release workflow run: `33162898643`，全部成功。
- 正式分发：GitHub Releases（不是 Actions Artifact）。
- 正式单文件：`TGExporter-v0.1.6-windows-x64.exe`
- EXE SHA-256：`37636dd62e481a4934104ceac2f8591238f9ec59696b78e1d475cda2e326ecef`
- Portable：`TGExporter-v0.1.6-windows-x64-portable.zip`

v0.1.6 将用户可见品牌统一缩短为：

```text
TG Exporter
TG 导出器
TGExporter.exe
```

兼容边界：

- Python distribution name：`tg-exporter`；
- 新 CLI：`tg-exporter`；旧 `telegram-multi-chat-exporter` 暂时保留；
- 内部 Python module 继续是 `telegram_exporter`；
- **不迁移** `%APPDATA%\TelegramMultiChatExporter\`，以继续复用已有 Session/API/settings/checkpoints/logs。

## 2. 用户已实际验证过什么

已由真实账号验证：

- Telegram API 登录成功。
- Windows 系统代理检测可识别 Clash `http://127.0.0.1:7890`。
- Telethon transport 通过该代理成功连接 Telegram。
- 账号 Session 可保存并复用。

曾由用户日志定位并修复：

1. 系统代理未被 Telethon 自动继承 → v0.1.2 起显式读取 Windows 系统代理。
2. qasync nested modal dialog 重入 → v0.1.3 改为非阻塞 dialog await 模式。
3. 关闭程序时 `await None` → v0.1.5 起已包含修复。

尚待用户真实账号 E2E：

- Telegram 分组下拉框是否与账号实际 Chat Folders 名称/成员一致；
- 关闭窗口是否不再弹 `Unhandled exception in script`；
- 新 `TGExporter.exe` 是否无缝复用旧 AppData Session/settings；
- 五个以上群的混合模式完整批次导出；
- `导出后标已读` 对手机/桌面端 read marker 的真实同步验证；
- 与 Telegram Desktop 同一群/同一时间窗口的 JSON differential test。

## 3. 当前用户可见能力

- Windows PySide6 GUI，品牌名 `TG Exporter / TG 导出器`。
- Telegram 首次手机号 / code / 2FA 登录与本地 Session 复用。
- Windows 系统代理自动检测与 Telethon 显式代理。
- 本地轮转日志、API 设置、重置登录、打开日志目录。
- 完整账号群组只作为后台 catalogue。
- `选择群组` 中可先选择 Telegram 账号已有 Chat Folder，再按群名 / `@username` 搜索和勾选。
- Telegram 文件夹只读；读取失败时退化为完整 catalogue + 搜索。
- 主面板只显示最终勾选的工作群，选择跨启动持久化。
- 每群独立模式：指定时间范围 / 当前未读 / 上次导出以后。
- 当前未读使用刷新时冻结快照。
- Option B：每群独立 `导出后标已读`，默认 OFF，仅未读模式可用。
- 每个群独立 `result.json`；每次运行独立批次目录。
- 文本/caption-only；不下载媒体。
- Telegram Desktop 风格核心 JSON 字段。
- one-file EXE + portable ZIP + SHA256SUMS Release 流程。

## 4. Telegram Chat Folder 实现说明

Telegram API 将聊天文件夹称为 **Dialog Filters**。当前实现：

- `telegram_service.list_groups()` 在加载 dialogs 后调用 `messages.getDialogFilters`；
- `dialog_filters.py` 把账号 filter 规则映射到 `GroupInfo.folders`；
- `group_selector.py` 从 folder refs 构造 `Telegram 分组` 下拉框；
- 文件夹筛选与文本搜索是 AND 关系；
- 一个群可同时属于多个 Telegram 文件夹。

动态规则覆盖 explicit include/pinned/exclude、groups、broadcasts、exclude_read、exclude_muted、exclude_archived。优先级：explicit exclude > explicit/pinned include > dynamic rules。`DialogFilterDefault` 不展示，因为选择器已有“全部群组/频道”。

## 5. 关键产品不变量

除非用户明确要求，不要改变：

- 不建设累计 master DB；历史批次不合并、不回写。
- 不下载照片/视频/语音/文件/贴纸；JSON 是权威数据源。
- 每群规则独立；主工作区只显示用户选中的少量群。
- Telegram Chat Folders 仅用于选择器筛选，不修改用户账号分组。
- 默认导出不改变 Telegram 已读状态；read ack 必须由用户按群明确开启，且 JSON 成功后才能发送。
- GUI-first。
- 产品展示名使用 `TG Exporter / TG 导出器`；AppData 兼容路径继续是 `%APPDATA%\TelegramMultiChatExporter\`。

更完整规则见 `AGENTS.md` 与 `docs/DECISIONS.md`。

## 6. 当前代码结构（重要）

启动链：

```text
launcher.py
→ telegram_exporter.main
→ telegram_exporter.focused_gui.MainWindow
```

GUI：`gui.py` → `gui_async.py` → `focused_gui.py`；`group_selector.py` 负责完整目录 + Telegram Folder + 搜索选择。

核心：`telegram_service.py`、`dialog_filters.py`、`models.py`、`proxy.py`、`exporter.py`、`read_state.py`、`desktop_json.py`、`storage.py`、`paths.py`、`logging_setup.py`、`diagnostics.py`。

## 7. 当前 JSON / 可靠性技术债

JSON 兼容缺口见 `docs/JSON_COMPATIBILITY.md`：rich text、真实 chat type/top-level id、whitespace、service/forward metadata 等。

优先级：

- P0/P1：真人验证 Telegram Folder、shutdown、旧 AppData 数据复用、Option B frozen upper bound。
- P1：`result.json` atomic write；重复清洗群名目录 collision；Desktop chat type/top-level id；原样 whitespace。
- P2：rich text；forward/service；每行实时进度/失败重试；GUI 三层收敛但保持 qasync safety。

## 8. 未读与已读语义

刷新 catalogue 时保存 `unread_count / read_inbox_max_id / latest_message_id`，本批未读窗口固定为：

```text
read_inbox_max_id < id <= latest_message_id
```

`导出后标已读`：

```text
write result.json success
→ local checkpoint
→ send_read_acknowledge(max_id=latest_message_id)
```

Telegram read marker 按 ID 推进，因此快照内未进入 JSON 的媒体/系统消息也可能一起变已读；UI 必须持续提示。

## 9. 本地文件与安全

兼容目录继续为：

```text
%APPDATA%\TelegramMultiChatExporter\
```

典型文件：`api_credentials.json`、`telegram.session`、`local_state.json`、`settings.json`、`logs\app.log`。

不要仅因为品牌改名就迁移这个目录。仓库和日志禁止出现 api_hash、手机号、验证码、2FA、Session 内容、聊天正文。

## 10. 发布与下一步

- `VERSION` 与 `pyproject.toml` 必须一致。
- 正式分发只用 GitHub Releases。
- 下一步让用户重点验证：①新短名称；②旧 Session/settings 无缝复用；③账号分组是否正确；④关闭窗口无 fatal dialog。
- 之后继续 JSON compatibility、atomic output 等工作。

## 11. 当前不做

除非用户重新提出：360/杀软误报与签名、完整媒体备份、云端消息数据库、自动绕过安全软件。
