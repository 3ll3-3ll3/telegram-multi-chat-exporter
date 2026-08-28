# Architecture

## 1. Product boundary

这是一个 **Windows GUI Telegram 多群独立批次文本导出器**，不是 Telegram 客户端替代品，也不是累计归档数据库。

每次运行：

1. 登录/复用一个 Telegram 用户账号 Session。
2. 加载账号完整群组/频道 catalogue。
3. 主界面只展示用户预先选择的少量工作群。
4. 每个工作群独立选择导出规则。
5. 读取本次规则命中的文本/caption。
6. 每个群写独立 `result.json`。
7. 所有群放入本次独立批次目录。
8. 历史批次不会被读取、合并或重写。

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
- current unread frozen snapshot；
- 每群 `导出后标已读` Option B；
- 与已有 qasync-safe dialog 层集成。

后续可以重构合并三层，但必须先补测试，且不得回退 qasync-safe 行为。

## 4. Telegram service

`telegram_service.py` 负责：

- 建立 Telethon `TelegramClient`；
- 首次登录/授权检查；
- code / 2FA；
- dialog catalogue；
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

## 6. Group catalogue 与 focused workspace

`telegram_service.list_groups()` 返回每个群的：

- marked `chat_id`
- title
- username
- unread_count
- read_inbox_max_id
- latest_message_id（刷新时最新消息）

完整列表进入 `GroupSelectorDialog`。主导出表只展示 `settings.json` 中 `selected_group_ids` 对应的工作群。

不要把完整 catalogue 再直接铺到主表格。

## 7. Export modes

### 7.1 Date range

按本地日期构造起止 datetime；应用层再做 inclusive boundary 检查。

### 7.2 Current unread

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

### 7.3 Since last export

使用 `LocalState.last_message_id(chat_id)` 作为 lower bound。

若该群从未有成功 checkpoint，必须提示用户先用 date range 或 current unread，不得默默从全部历史开始。

checkpoint 单调不减：后来导出更早历史窗口不能让 since-last 倒退。

## 8. Read-state Option B

默认导出是只读的，不改变 Telegram read marker。

用户可为某群在 `当前未读` 模式明确开启：

```text
导出后标已读
```

严格执行顺序：

```text
1. result.json 成功写入
2. local checkpoint 更新
3. send_read_acknowledge(max_id=frozen upper)
```

约束：

- export failed → no read ack；
- read ack failed → JSON 保留，单独报告；
- new messages after catalogue refresh → 不导出、不标已读；
- Telegram read marker 按 ID 推进，所以快照内未进入纯文本 JSON 的 media/service item 可能一起变已读。

## 9. Export pipeline

`exporter.py`：

```text
GroupExportPlan
→ resolve Telegram entity
→ iter_messages with mode bounds
→ skip non-Message / no-text items
→ resolve sender/reply/edit metadata
→ ExportMessage list
→ desktop_json.build_chat_export()
→ <batch>/<safe group folder>/result.json
```

媒体文件从不下载。`message.message` 可包含普通文本或媒体 caption。

## 10. JSON serialization

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

兼容边界与已知差异见 `JSON_COMPATIBILITY.md`。

## 11. Local storage

默认根目录：

```text
%APPDATA%\TelegramMultiChatExporter\
```

- `api_credentials.json`：api_id/api_hash，本机 only。
- `telegram.session`：Telethon Session，本机 only。
- `local_state.json`：每群 checkpoint，本机 only。
- `settings.json`：输出目录、工作群选择、每群 UI/read policy preference。
- `logs/app.log`：轮转日志，不记录聊天正文或验证码等 Secret。

`storage.write_json_atomic()` 用 `.tmp → replace` 写 settings/state。

**当前 `result.json` 的 atomic write 仍是待改进项。**

## 12. Logging / diagnostics

日志默认：

```text
%APPDATA%\TelegramMultiChatExporter\logs\app.log
```

日志用于区分：

- proxy detection；
- Telegram transport；
- authorization；
- code / 2FA 阶段；
- export per group；
- read ack；
- shutdown。

日志禁止记录：api_hash、phone、code、2FA password、session contents、chat body。

## 13. Shutdown

Qt `aboutToQuit` 设置 async close event，`_run_app()` 随后调用 `window.shutdown()`。

Telethon `disconnect()` 在不同 loop 状态下可能返回 awaitable 或直接完成；service close 必须兼容两种情况。

shutdown 清理异常只应记录日志，不应成为 PyInstaller 顶层 fatal dialog。

## 14. Security boundary

GitHub Actions 构建不需要 Telegram Secret。

公开仓库禁止提交：

```text
*.session
api_credentials.json
local_state.json
settings.json (真实用户副本)
logs
exports
验证码/手机号/2FA
```

## 15. 当前主要技术债

按优先级：

1. 发布 main 上 shutdown hotfix 并真人验证。
2. `result.json` atomic write。
3. sanitized duplicate group-title folder collision。
4. Telegram Desktop chat type / top-level id differential test。
5. preserve original whitespace。
6. rich text entity mapping。
7. service/forward metadata 策略。
8. GUI 三层结构收敛（必须保持 qasync safety）。
9. per-row message progress / retry failed rows。
