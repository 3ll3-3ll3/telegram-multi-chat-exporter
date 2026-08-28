# HANDOFF.md

> 这是本仓库的**当前开发交接快照**。任何 Agent 接手前先读 `AGENTS.md`，再读本文件。完成用户可见功能、关键修复或 Release 后必须更新本文件。

更新时间：2026-08-28

## 1. 当前版本状态

### 最新正式 Release

- 当前已发布：**v0.1.5**
- Release: `https://github.com/3ll3-3ll3/telegram-multi-chat-exporter/releases/tag/v0.1.5`
- Release target commit: `bf42ac79374d8ccf078a3f22bdb7d785bc46fb3c`
- 正式分发：GitHub Releases（不是 Actions Artifact）

### v0.1.6 candidate

当前分支 `chore/short-name-v0.1.6` 准备发布 **v0.1.6**，目标是缩短项目用户可见名称：

```text
TG Exporter
TG 导出器
TGExporter.exe
```

同时：

- `pyproject.toml` distribution name 改为 `tg-exporter`；
- 新 CLI 名为 `tg-exporter`，旧 `telegram-multi-chat-exporter` 暂时保留兼容；
- Windows CI / Release 构建产物改为 `TGExporter`；
- Release 资产改成 `TGExporter-vX.Y.Z-windows-x64.*`；
- Release 标题改成 `TG Exporter vX.Y.Z`；
- **不迁移** `%APPDATA%\TelegramMultiChatExporter\`，保证已有 Session/API/settings/logs 无缝复用；
- 内部 Python module `telegram_exporter` 保持不变，避免无价值的大范围 import 重构。

`VERSION=v0.1.6`，`pyproject.toml=0.1.6`。Windows CI 全绿后应以 `release: v0.1.6` squash merge 到 main，由 release workflow 创建正式 Release。

## 2. 用户已实际验证过什么

已由真实账号验证：

- Telegram API 登录成功。
- Windows 系统代理检测可识别 Clash `http://127.0.0.1:7890`。
- Telethon transport 通过该代理成功连接 Telegram。
- 账号 Session 可保存并复用。

曾由用户日志定位并修复：

1. **系统代理未被 Telethon 自动继承** → v0.1.2 起显式读取 Windows 系统代理。
2. **qasync nested modal dialog 重入** → v0.1.3 改为非阻塞 dialog await 模式。
3. **关闭程序时 `await None`** → v0.1.5 已包含修复。

尚待用户真实账号 E2E：

- Telegram 分组下拉框是否与账号实际 Chat Folders 名称/成员一致；
- v0.1.5+ 关闭窗口是否不再弹 `Unhandled exception in script`；
- 五个以上群的混合模式完整批次导出；
- `导出后标已读` 对手机/桌面端 read marker 的真实同步验证；
- 与 Telegram Desktop 同一群/同一时间窗口的 JSON differential test。

v0.1.6 发布后还需确认：旧 AppData 数据是否被新 `TGExporter.exe` 正常复用。

## 3. 当前用户可见能力

- Windows PySide6 GUI。
- Telegram 首次手机号 / code / 2FA 登录与本地 Session 复用。
- Windows 系统代理自动检测与 Telethon 显式代理。
- 本地轮转日志、API 设置、重置登录、打开日志目录。
- 完整账号群组只作为后台 catalogue。
- `选择群组` 中可先选择 **Telegram 分组**（账号已有 Chat Folder），再按群名 / `@username` 搜索和勾选。
- 只显示包含至少一个群组/频道的 Telegram 文件夹；私聊/机器人-only 文件夹对本工具无可选目标，因此省略。
- Telegram 文件夹只读：不创建、不修改、不删除账号内分组。
- Telegram 文件夹加载失败时退化为原来的完整 catalogue + 搜索，不阻断主功能。
- 主面板只显示最终勾选的固定工作群，选择跨启动持久化。
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
- `dialog_filters.py` 负责把账号 filter 规则映射到 `GroupInfo.folders`；
- `group_selector.py` 从每个 group 的 folder refs 构造 `Telegram 分组` 下拉框；
- 文件夹筛选与文本搜索是 AND 关系；
- 一个群可同时属于多个 Telegram 文件夹。

动态规则当前覆盖：

- explicit `include_peers` / `pinned_peers`；
- explicit `exclude_peers`；
- `groups`；
- `broadcasts`；
- `exclude_read`；
- `exclude_muted`；
- `exclude_archived`。

优先级：explicit exclude > explicit/pinned include > dynamic type/exclusion rules。

`DialogFilterDefault` 不作为自定义文件夹展示；选择器已有“全部群组/频道”。

## 5. 关键产品不变量

不要改变以下方向，除非用户明确要求：

- 不是累计归档库；不建设 master DB。
- 历史批次不合并、不回写。
- 不下载照片/视频/语音/文件/贴纸。
- JSON 是权威数据源。
- 每群规则独立。
- 主工作区只显示用户选中的少量群。
- Telegram Chat Folders 仅用于选择器筛选，不修改用户账号分组。
- 默认导出不改变 Telegram 已读状态。
- read acknowledgement 只能在用户为该群明确启用 `导出后标已读` 后发送。
- 导出 JSON 成功后才能标已读。
- GUI-first，最终用户不应依赖 CLI。
- 产品展示名从 v0.1.6 起使用 `TG Exporter / TG 导出器`；本地 AppData 兼容路径仍为 `%APPDATA%\TelegramMultiChatExporter\`。

更完整规则见 `AGENTS.md` 与 `docs/DECISIONS.md`。

## 6. 当前代码结构（重要）

启动链：

```text
launcher.py
→ telegram_exporter.main
→ telegram_exporter.focused_gui.MainWindow
```

GUI 层次：

- `gui.py`：早期基础 GUI/通用实现。
- `gui_async.py`：qasync-safe 非阻塞 dialog 层。
- `focused_gui.py`：当前实际主界面、focused workspace、未读快照、Option B。
- `group_selector.py`：完整群目录 + Telegram Folder + 文本搜索/选择弹窗。

服务与模型：

- `telegram_service.py`：Telethon client、登录、dialog catalogue、Dialog Filters、代理、disconnect。
- `dialog_filters.py`：Telegram account folder membership evaluator。
- `models.py`：`GroupInfo` / `FolderRef` / `GroupExportPlan` / `ExportMode`。
- `proxy.py`：Windows 系统代理。
- `exporter.py`：按计划读取并写每群 `result.json`。
- `read_state.py`：显式 read acknowledgement。
- `desktop_json.py`：Telegram Desktop 风格 serializer。
- `storage.py` / `paths.py`：本地状态与路径。
- `logging_setup.py` / `diagnostics.py`：日志和用户错误提示。

## 7. 当前 JSON / 可靠性技术债

JSON 兼容缺口见 `docs/JSON_COMPATIBILITY.md`：rich text、真实 chat type/top-level id、whitespace、service/forward metadata 等。

可靠性优先级：

### P0/P1

- 真人验证 Telegram Folder 映射 + shutdown fix + v0.1.6 旧 AppData 数据复用。
- 真实账号测试 `导出后标已读` 的 frozen upper bound。

### P1

- `result.json` atomic write。
- sanitized duplicate group-title directory collision。
- Telegram Desktop chat type / top-level id differential test。
- 原样保存文字 whitespace。

### P2

- rich text entity mapping。
- forward/service 纯文本兼容策略。
- 每行实时消息进度、失败群一键重试。
- GUI 三层结构收敛，但不可牺牲 qasync safety。

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

**不要仅因为产品改名就迁移这个目录。** 仓库和日志禁止出现 api_hash、手机号、验证码、2FA、Session 内容、聊天正文。

## 10. 发布与下一步

- `VERSION` 与 `pyproject.toml` 必须一致。
- 正式分发只用 GitHub Releases。
- v0.1.6 发布成功后，把本文件顶部改成 v0.1.6 已发布并记录 release commit / CI。
- 下一步让用户重点验证：①新短名称；②旧 Session/settings 无缝复用；③账号分组是否正确；④关闭窗口无 fatal dialog。
- 之后再继续 JSON compatibility、atomic output 等工作。

## 11. 当前不做

除非用户重新提出：360/杀软误报与签名、完整媒体备份、云端消息数据库、自动绕过安全软件。
