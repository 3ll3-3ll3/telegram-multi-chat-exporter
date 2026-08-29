# Architecture

## 1. Product boundary

TG Exporter 包含两个本地入口，但共享同一 Telegram Core：

```text
Windows GUI exporter
Codex-callable tgctl CLI
        ↓
TelegramService
        ↓
Telethon user account
```

GUI 仍负责多群独立文本导出；v0.1.9 起 `tgctl` 负责手动、确定性的 Telegram 读取/搜索/真正转发/纯文本发送。本版没有 MCP、后台 daemon、长期监听、Bot API、规则引擎或 AI Agent。

GUI 输出仍为：

```text
总输出目录 / 分类 / 群组 / YYYY-MM-DD_HH-mm-ss.json
```

历史 JSON 不读取、不合并、不回写。

## 2. 启动链

GUI：

```text
launcher.py
→ telegram_exporter.main
→ QApplication + qasync.QEventLoop
→ focused_gui.MainWindow
```

CLI：

```text
tgctl_launcher.py / python -m telegram_exporter.tgctl
→ telegram_exporter.tgctl.main()
→ asyncio.run()
→ TelegramService
```

`tgctl` 不导入 Qt/qasync。CLI 与 GUI 不共享进程事件循环，只共享 Telegram Core、Session、proxy 和数据模型。

## 3. GUI 层

历史继承链仍是：

```text
gui.py
→ gui_async.py
→ focused_gui.py
```

- `gui.py`：基础连接/导出 GUI；
- `gui_async.py`：qasync-safe non-blocking dialog；
- `focused_gui.py`：focused workspace、Telegram Folder、头像、Export Category、Option B、migration UI preference。

禁止在 Telethon 活跃的 async slot 中重新引入 blocking modal nested event loop。

## 4. TelegramService

`telegram_service.py` 是 GUI / tgctl / 未来 MCP 应复用的 Telegram Core。当前职责：

```text
connect / authorization state
phone/code/2FA methods（仅 GUI 首次登录使用）
account_info
list_groups
resolve_group
search_messages
get_messages
forward_messages
send_text_message
group_avatar_bytes
close
```

CLI 不调用 phone/code/2FA 登录方法；它只复用 GUI 已创建的授权 Session。

`list_groups()` 仍负责：

- groups/channels catalogue；
- Basic Group → Supergroup migration collapse；
- Dialog Filters / Chat Folder memberships；
- unread snapshot traits；
- avatar capability metadata。

因此 tgctl 不维护第二份 chat catalogue 实现。

## 5. Shared Session ownership

兼容 Session base：

```text
%APPDATA%\TelegramMultiChatExporter\telegram
```

Telethon 常见文件：`telegram.session`。

v0.1.9 起 `TelegramService.__init__()` 在创建 `TelegramClient` 前获取 `SessionLease`：

```text
%APPDATA%\TelegramMultiChatExporter\telegram.session.lock
```

锁使用 OS-level non-blocking file lock。目的不是用 lock file 的“存在性”判断占用，而是依赖 OS 持有的文件锁；崩溃后 OS 自动释放实际锁。

结果：

```text
GUI owns session → tgctl gets SESSION_BUSY
tgctl owns session → GUI gets SessionBusyError
```

`close()` 无论 client 是否已经 connected，都在 finally 释放 SessionLease。

第一版明确不允许两个进程同时打开同一 Telethon SQLiteSession。未来多客户端应改成 single daemon + IPC，而不是绕过 lock。

## 6. Credentials / proxy

本地文件：

```text
%APPDATA%\TelegramMultiChatExporter\api_credentials.json
%APPDATA%\TelegramMultiChatExporter\telegram.session
```

`credentials_store.load_saved_credentials()` 给 CLI 读取已有 API credentials。CLI 缺失/未授权时返回 `NOT_AUTHORIZED`，不做交互式登录。

`proxy.py` 检测 Windows system proxy 并显式传给 Telethon。tgctl 与 GUI 走同一逻辑。

## 7. tgctl command pipeline

```text
argv
→ argparse deterministic parser
→ pre-connect safety validation
→ open existing authorized TelegramService
→ service operation
→ dataclass/dict result
→ stable JSON envelope or human output
→ service.close()
```

JSON success：

```json
{"ok":true,"data":{}}
```

JSON failure：

```json
{"ok":false,"error":{"code":"...","message":"...","details":{}}}
```

JSON mode stdout 不混入 logging。`setup_logging()` 只写本地 rotating file。

## 8. Chat resolution

`resolve_group()` 接受：

- marked integer chat_id；
- 精确 `@username`；
- 精确 title。

同名 title 多个时抛 `AMBIGUOUS_CHAT`，带安全候选：chat_id/title/username/type。禁止 first-match 猜测。

Saved Messages 在 write destination 上使用显式 `me`，不经过 catalogue title resolution。

## 9. Message reads

`search_messages()`：

- current logical chat only；
- deterministic `contains / since / until / limit / case_sensitive`；
- `since` inclusive、`until` exclusive；
- text/caption only；
- 不下载媒体；
- 返回 chat id/title、message id、date、sender label、text。

`get_messages()`：按 ids 精确取消息；任一缺失返回 `MESSAGE_NOT_FOUND` + missing ids。

CLI 第一版不做 migrated legacy + current 的跨 peer 搜索；GUI date-range historical stitching 继续保留且不受影响。tgctl catalogue 仍隐藏 legacy duplicate。

## 10. Write operations

### forward

`forward_messages()` 预取 ids 做安全检查，然后调用 Telethon `client.forward_messages(...)`。不是复制正文重新 send。

第一版只让纯文本/普通网页 preview 进入 true forward；照片/视频/文件/语音等媒体消息作为 `failed_ids`，避免本版偷偷扩成媒体转发器。

### send

`send_text_message()` 使用：

```text
parse_mode=None
link_preview=False
```

只做纯文本。

### dry-run

forward/send dry-run 完成相同的 chat resolution / id preflight，但不调用 Telegram write method。

CLI 层 forward 有两级批量闸门：默认 20，显式 `--allow-large-batch` 后 200 hard cap。

FloodWait 向上返回给 CLI 映射为结构化错误；不做 retry loop。

## 11. GUI export pipeline

原有行为不变：

```text
GroupExportPlan
→ current entity
→ optional legacy entity for DATE_RANGE
→ text/caption collection
→ Desktop-style serializer
→ output/category/group/timestamp.json
→ atomic tmp -> replace
→ checkpoint
→ optional Option B read ack
```

current unread 使用 frozen snapshot；since-last checkpoint 单调不减。

## 12. Local storage / logging

```text
%APPDATA%\TelegramMultiChatExporter\
├─ api_credentials.json
├─ telegram.session
├─ telegram.session.lock
├─ local_state.json
├─ settings.json
├─ logs\app.log
└─ cache\avatars\
```

日志可记录阶段、proxy safe label、api_id、chat/message id、数量、write success/failure。

日志禁止：api_hash、phone、OTP、2FA、Session contents、chat message body、avatar bytes。

`messages search/get` 的正文只在命令明确请求的 stdout 数据中出现，不写普通日志。

## 13. Packaging

v0.1.9 Release：

```text
TGExporter-vX.Y.Z-windows-x64.exe
TGExporter-vX.Y.Z-windows-x64-portable.zip
  └─ TGExporter/TGExporter.exe + tgctl.exe
tgctl.exe
SHA256SUMS.txt
```

CI 对 GUI 与 tgctl 都执行 PyInstaller packaged smoke-test。

## 14. Future MCP direction

推荐：

```text
single local Telegram daemon owns Session
├─ GUI IPC client
├─ tgctl IPC client
└─ MCP IPC client
```

需要新增 IPC protocol、daemon lifecycle/crash recovery、本机客户端鉴权、MCP tool schema 与 write confirmation policy。本版不实现这些。
