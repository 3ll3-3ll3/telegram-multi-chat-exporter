# HANDOFF.md

> 这是本仓库的**当前开发交接快照**。任何 Agent 接手前先读 `AGENTS.md`，再读本文件。完成用户可见功能、关键修复或 Release 后必须更新本文件。

更新时间：2026-08-29

## 1. 当前版本状态

### 最新正式 Release

- 当前已发布：**TG Exporter v0.1.7**
- 仓库：`https://github.com/3ll3-3ll3/tg-exporter`
- Release: `https://github.com/3ll3-3ll3/tg-exporter/releases/tag/v0.1.7`
- Release target commit: `63034d2e15677e2579af5763a89b8a9fe81143ff`
- Release workflow run: `33227209870`，全部成功。
- 正式分发：GitHub Releases（不是 Actions Artifact）。
- 正式单文件：`TGExporter-v0.1.7-windows-x64.exe`
- EXE SHA-256：`22a67e7551cb60e983734106aa9cc92b2f48dce85c8142372f11668252f03629`
- Portable：`TGExporter-v0.1.7-windows-x64-portable.zip`
- Portable SHA-256：`0fb39d291de486972a98701791a3dd21e5005d18cec80c61004077fc702c48b3`

v0.1.7 正式包含群组选择器头像与大尺寸记录：

- 约 **42 px 圆形头像 + 58 px 行高**；
- 双行信息：群名 + `@username` / 群组或频道 / 未读数；
- 无头像或头像尚未加载时使用确定性的圆形首字占位；
- Telegram 小头像只对当前屏幕附近可见项**按需异步加载**；
- 最大头像并发 6，避免账号有数百群时突发下载；
- 成功头像缓存在 `%APPDATA%\TelegramMultiChatExporter\cache\avatars\`，默认约 7 天；
- 头像失败只保留占位，不影响选择器、登录或导出；
- 头像只是 UI 元数据，不进入 `result.json`，不复制到导出批次；
- 聊天消息本身仍严格 text/caption-only，不下载聊天里的图片/视频/文件。

正式 Release 流水线已通过：Test、GUI import、one-file build、portable build、两种 packaged smoke-test、release assets 和 GitHub Release 上传。

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
- **v0.1.7 真实群头像是否正确显示，滚动/分组/搜索时是否按需加载且不卡顿；**
- 无头像群是否稳定显示首字占位；
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
- v0.1.7 起选择器显示按需加载的圆形群头像与更大的双行记录。
- Telegram 文件夹只读；读取失败时退化为完整 catalogue + 搜索。
- 主面板只显示最终勾选的工作群，选择跨启动持久化。
- 每群独立模式：指定时间范围 / 当前未读 / 上次导出以后。
- 当前未读使用刷新时冻结快照。
- Option B：每群独立 `导出后标已读`，默认 OFF，仅未读模式可用。
- 每个群独立 `result.json`；每次运行独立批次目录。
- 消息 text/caption-only；不下载聊天媒体。
- Telegram Desktop 风格核心 JSON 字段。
- one-file EXE + portable ZIP + SHA256SUMS Release 流程。

## 4. Telegram Chat Folder / Avatar 实现说明

Telegram API 将聊天文件夹称为 **Dialog Filters**。当前实现：

- `telegram_service.list_groups()` 在加载 dialogs 后调用 `messages.getDialogFilters`；
- `dialog_filters.py` 把账号 filter 规则映射到 `GroupInfo.folders`；
- `group_selector.py` 从 folder refs 构造 `Telegram 分组` 下拉框；
- 文件夹筛选与文本搜索是 AND 关系；
- 一个群可同时属于多个 Telegram 文件夹。

动态规则覆盖 explicit include/pinned/exclude、groups、broadcasts、exclude_read、exclude_muted、exclude_archived。优先级：explicit exclude > explicit/pinned include > dynamic rules。`DialogFilterDefault` 不展示，因为选择器已有“全部群组/频道”。

v0.1.7 avatar path：

```text
GroupInfo.has_photo
→ GroupSelectorDialog 当前可见行
→ TelegramService.group_avatar_bytes(group)
→ fresh local cache or Telethon download_profile_photo(..., file=bytes, download_big=False)
→ circular QIcon
```

缓存 helper：`avatar_cache.py`；缓存目录由 `paths.avatar_cache_dir()` 提供。不要在 catalogue 刷新阶段一次性下载全部头像。

## 5. 关键产品不变量

除非用户明确要求，不要改变：

- 不建设累计 master DB；历史批次不合并、不回写。
- 聊天消息不下载照片/视频/语音/文件/贴纸；JSON 是权威数据源。
- 群/频道资料头像仅是选择器 UI 例外，不属于聊天媒体导出。
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

GUI：`gui.py` → `gui_async.py` → `focused_gui.py`；`group_selector.py` 负责完整目录 + Telegram Folder + 搜索选择 + avatar UI。

核心：`telegram_service.py`、`dialog_filters.py`、`avatar_cache.py`、`models.py`、`proxy.py`、`exporter.py`、`read_state.py`、`desktop_json.py`、`storage.py`、`paths.py`、`logging_setup.py`、`diagnostics.py`。

## 7. 当前 JSON / 可靠性技术债

JSON 兼容缺口见 `docs/JSON_COMPATIBILITY.md`：rich text、真实 chat type/top-level id、whitespace、service/forward metadata 等。

优先级：

- P0/P1：真人验证 v0.1.7 avatar selector；继续验证 Telegram Folder、shutdown、旧 AppData 数据复用、Option B frozen upper bound。
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

头像读取不得发送 read acknowledgement，也不得改变消息已读状态。

## 9. 本地文件与安全

兼容目录继续为：

```text
%APPDATA%\TelegramMultiChatExporter\
```

典型文件：`api_credentials.json`、`telegram.session`、`local_state.json`、`settings.json`、`logs\app.log`、`cache\avatars\*`。

不要仅因为品牌改名就迁移这个目录。仓库和日志禁止出现 api_hash、手机号、验证码、2FA、Session 内容、聊天正文；头像 cache 二进制也不得提交仓库。

## 10. 发布与下一步

- `VERSION` 与 `pyproject.toml` 必须一致。
- 正式分发只用 GitHub Releases。
- 当前正式版为 v0.1.7；main 在本次 HANDOFF 更新之前无额外功能性未发布变更。
- 用户重点验证：①真实群头像；②滚动/Telegram 分组/搜索切换时不卡顿；③无头像群使用首字占位；④旧 Session/settings 继续复用。
- 之后继续 JSON compatibility、atomic output 等工作。

## 11. 当前不做

除非用户重新提出：360/杀软误报与签名、完整聊天媒体备份、云端消息数据库、自动绕过安全软件。
