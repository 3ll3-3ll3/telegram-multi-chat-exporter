# Architecture

## 1. Product boundary

这是一个 **Windows GUI Telegram 多群独立文本导出器**，不是 Telegram 客户端替代品，也不是累计归档数据库。

一次用户操作通常经历：

1. 登录/复用一个 Telegram 用户账号 Session。
2. 加载账号完整群组/频道 catalogue。
3. 隐藏 migrated legacy Basic Group，只保留当前 Supergroup 作为逻辑群。
4. 主界面只展示用户预先选择的少量工作群。
5. 每个工作群独立选择导出分类与导出规则。
6. 读取本次规则命中的文本/caption。
7. 每个群写一个新的独立 JSON 到：

```text
总输出目录 / 分类 / 群组 / YYYY-MM-DD_HH-mm-ss.json
```

8. 历史 JSON 不被读取、合并或重写。

`local_state.json` 只为 “since last export” 保存每群 checkpoint，不保存消息正文。

## 2. 启动链

当前实际启动路径：

```text
launcher.py
  └─ telegram_exporter.main.main()
       └─ QApplication + qasync.QEventLoop
            └─ focused_gui.MainWindow
```

`launcher.py --smoke-test` 用于 PyInstaller 打包后 CI 导入验证，不进行真实 Telegram 登录。

## 3. GUI 层次

当前存在历史演进形成的三层 GUI：

```text
gui.py
  └─ gui_async.py
       └─ focused_gui.py   ← 当前实际 MainWindow
```

### `gui.py`

早期基础 GUI、表格、基础连接/导出流程。

### `gui_async.py`

解决 qasync + Telethon 的 nested modal event-loop 问题：

- 使用 `dialog.open()`；
- await `finished` signal；
- 避免在 async slot 内调用 blocking `exec()` / static QMessageBox / static QInputDialog。

### `focused_gui.py`

当前用户实际使用的最终窗口层：

- 群组 catalogue 与 focused workspace；
- searchable group selector；
- Telegram Chat Folder 筛选；
- 每群本地导出分类；
- `管理分类` 非阻塞 dialog；
- current unread frozen snapshot；
- 每群 `导出后标已读` Option B；
- migrated old peer UI 偏好迁移；
- 新的分类/群组/时间戳输出路径。

后续可以重构合并三层，但必须先补测试，且不得回退 qasync-safe 行为。

## 4. Telegram service

`telegram_service.py` 负责：

- 建立 Telethon `TelegramClient`；
- 首次登录/授权检查；
- code / 2FA；
- dialog catalogue；
- Basic Group -> Supergroup migration collapse；
- Telegram Dialog Filters / Chat Folders；
- 群头像按需读取；
- 连接关闭；
- 将 Windows system proxy 显式传给 Telethon。

Telethon Session 基址：

```text
%APPDATA%\TelegramMultiChatExporter\telegram
```

实际常见文件为 `telegram.session`。

## 5. Windows proxy

`proxy.py` 检测 Windows 已启用的系统代理。典型 Clash/Mihomo：

```text
http://127.0.0.1:7890
```

原因：Telethon 使用原生网络连接，不能假设像浏览器一样自动继承 Windows proxy，也不能假设继承 Telegram Desktop 自己的代理设置。

代理信息在日志中只输出安全端点标签，不输出 Telegram Secret。

## 6. Group catalogue、迁移与 focused workspace

`telegram_service.list_groups()` 先读取 dialogs，再识别旧 Basic Group entity 的 `migrated_to`：

```text
legacy Basic Group
  migrated_to -> current Supergroup
```

legacy row 不进入最终 catalogue；其 marked peer id 写入当前 `GroupInfo.migrated_from_chat_id`。

最终每个 `GroupInfo` 可包含：

- marked `chat_id`（当前逻辑群）
- title
- username
- unread_count
- read_inbox_max_id
- latest_message_id（刷新时最新消息）
- migrated_from_chat_id（可选）
- avatar / group / broadcast / muted / archived / unread traits
- Telegram folder refs

完整列表进入 `GroupSelectorDialog`。主导出表只展示 `settings.json` 中 `selected_group_ids` 对应的工作群。

如果旧 migrated peer 曾存在于 selected/read/category UI 配置，`focused_gui` 将这些 UI 设置迁到当前超级群；**不会把旧 local checkpoint 直接复制到新 peer**。

不要把完整 catalogue 再直接铺到主表格。

## 7. Telegram Chat Folder vs Export Category

这两者严格分离。

### Telegram Chat Folder

- 来源：Telegram 账号 `messages.getDialogFilters`；
- 作用：选择器里筛选 catalogue；
- 权限：只读；
- 不决定本地文件路径。

### Export Category

- 来源：TG Exporter 本地 `settings.json`；
- 作用：决定 JSON 落盘的一级目录；
- UI：`管理分类` + 主表每群分类 ComboBox；
- 内置默认：`未分类`；
- 自定义分类：`settings.export_categories`；
- 每群绑定：`settings.group_export_categories`。

`export_categories.py` 负责 Windows-safe 分类名校验、目录创建、时间戳命名和同秒冲突避免。

## 8. Export modes

### 8.1 Date range

按本地日期构造起止 datetime；应用层再做 inclusive boundary 检查。

若 `migrated_from_chat_id` 存在：

```text
legacy Basic Group history
+ current Supergroup history
→ merge by (date, id)
→ one JSON
```

legacy history不更新当前超级群的 since-last checkpoint；只有当前 Supergroup 读取到的 message id 可用于当前 checkpoint。

### 8.2 Current unread

刷新 catalogue 时冻结：

```text
lower = read_inbox_max_id
upper = latest_message_id
```

导出窗口：

```text
lower < message_id <= upper
```

Telethon 查询通过 `min_id` 与 exclusive `max_id = upper + 1` 表达。

如果 `unread_count <= 0`，应输出合法空结果，不得退化为 `min_id=0` 遍历全部历史。

migrated group 的 current unread 只针对当前 Supergroup。

### 8.3 Since last export

使用 `LocalState.last_message_id(current_chat_id)` 作为 lower bound。

若该群从未有成功 checkpoint，必须提示用户先用 date range 或 current unread，不得默默从全部历史开始。

checkpoint 单调不减：后来导出更早历史窗口不能让 since-last 倒退。

migrated legacy Chat 的旧 checkpoint 不自动复制到当前 Supergroup。

## 9. Read-state Option B

默认导出是只读的，不改变 Telegram read marker。

用户可为某群在 `当前未读` 模式明确开启：

```text
导出后标已读
```

严格执行顺序：

```text
1. 本次 JSON 成功原子写入
2. local checkpoint 更新
3. send_read_acknowledge(max_id=frozen upper)
```

约束：

- export failed → no read ack；
- read ack failed → JSON 保留，单独报告；
- new messages after catalogue refresh → 不导出、不标已读；
- Telegram read marker 按 ID 推进，所以快照内未进入纯文本 JSON 的 media/service item 可能一起变已读。

## 10. Export pipeline

`exporter.py`：

```text
GroupExportPlan(category + mode)
→ resolve current Telegram entity
→ optional resolve legacy migrated entity for DATE_RANGE
→ iter_messages with mode bounds
→ skip non-Message / no-text items
→ resolve sender/reply/edit metadata
→ optional merge legacy + current by time
→ desktop_json.build_chat_export()
→ output_root/category/safe_group/YYYY-MM-DD_HH-mm-ss.json
→ atomic tmp -> replace
```

同秒已有同名文件时：

```text
..._HH-mm-ss.json
..._HH-mm-ss_2.json
..._HH-mm-ss_3.json
```

媒体文件从不下载。`message.message` 可包含普通文本或媒体 caption。

## 11. JSON serialization

`desktop_json.py` 输出 Telegram Desktop 风格核心结构：

```text
name / type / id / messages
```

普通消息核心字段：

```text
id
type
date
date_unixtime
from
from_id
reply_to_message_id
edited
edited_unixtime
text
text_entities
```

迁移群跨 legacy/current 合并时当前保留各自原 message id，不擅自重编号。

兼容边界与已知差异见 `JSON_COMPATIBILITY.md`。

## 12. Local storage

默认根目录：

```text
%APPDATA%\TelegramMultiChatExporter\
```

- `api_credentials.json`：api_id/api_hash，本机 only。
- `telegram.session`：Telethon Session，本机 only。
- `local_state.json`：每群当前 peer checkpoint，本机 only。
- `settings.json`：输出根目录、工作群选择、每群 read policy、导出分类列表、每群分类分配。
- `logs/app.log`：轮转日志，不记录聊天正文或验证码等 Secret。
- `cache/avatars/`：选择器小头像缓存。

`storage.write_json_atomic()` 用 `.tmp → replace` 写 settings/state；`exporter._write_export_json_atomic()` 对聊天 JSON 使用相同原子写入思想，同时保留当前 indent=1 输出格式。

## 13. Logging / diagnostics

日志默认：

```text
%APPDATA%\TelegramMultiChatExporter\logs\app.log
```

日志用于区分：

- proxy detection；
- Telegram transport；
- authorization；
- code / 2FA 阶段；
- catalogue migration collapse；
- export per group/category/path；
- read ack；
- shutdown。

日志禁止记录：api_hash、phone、code、2FA password、session contents、chat body。

## 14. Shutdown

Qt `aboutToQuit` 设置 async close event，`_run_app()` 随后调用 `window.shutdown()`。

Telethon `disconnect()` 在不同 loop 状态下可能返回 awaitable 或直接完成；service close 必须兼容两种情况。

shutdown 清理异常只应记录日志，不应成为 PyInstaller 顶层 fatal dialog。

## 15. Security boundary

GitHub Actions 构建不需要 Telegram Secret。

公开仓库禁止提交：

```text
*.session
api_credentials.json
local_state.json
settings.json (真实用户副本)
logs
exports
avatar cache
验证码/手机号/2FA
```

软件内删除导出分类不得递归删除历史用户数据。

## 16. 当前主要技术债

按优先级：

1. 真人验证 v0.1.8 分类目录和 migrated supergroup 行为。
2. sanitized duplicate group-title folder collision。
3. Telegram Desktop chat type / top-level id differential test。
4. preserve original whitespace。
5. rich text entity mapping。
6. service/forward metadata 策略。
7. migrated legacy/current message id 可能重叠时与 Telegram Desktop 的精确兼容策略。
8. GUI 三层结构收敛（必须保持 qasync safety）。
9. per-row message progress / retry failed rows。
