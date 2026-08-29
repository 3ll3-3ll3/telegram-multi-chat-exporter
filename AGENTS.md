# AGENTS.md

本文件是任何后续 Agent / Codex / 自动化开发者进入本仓库后的**第一阅读入口**。除非用户明确改变产品方向，否则以下规则视为项目长期不变量。

## 1. 开工前必须阅读

按顺序阅读：

1. `AGENTS.md`
2. `HANDOFF.md`
3. `docs/ARCHITECTURE.md`
4. `docs/DECISIONS.md`
5. `docs/TESTING.md`
6. `docs/RELEASE_PROCESS.md`
7. `SECURITY.md`
8. 涉及 CLI/Codex 时读 `docs/CODEX_TGCTL.md`
9. 涉及 JSON 兼容时读 `docs/JSON_COMPATIBILITY.md`

不要仅凭 README 推断当前实现状态；`HANDOFF.md` 才是开发交接快照。

## 2. 产品核心定位

TG Exporter 以 **Windows GUI Telegram 多群独立文本导出器**为主，从 v0.1.9 起同时包含一个**本地 `tgctl` CLI Bridge**，供 Codex 手动调用用户自己的 Telegram Session。

这不是 Telegram 客户端替代品、累计归档数据库、Bot API 产品、MCP Server、长期监听服务或 AI 自主 Agent。

GUI 导出必须保持：

- 每次对某群导出都是独立 JSON；历史 JSON 不读取、不合并、不回写。
- 输出：`总输出目录 / 导出分类 / 群组 / YYYY-MM-DD_HH-mm-ss.json`。
- 同秒冲突追加 `_2/_3/...`，不得覆盖。
- Export Category 是 TG Exporter 本地分类，不是 Telegram Chat Folder。
- 每群独立 date range / current unread / since last export。
- 聊天消息不下载照片/视频/文件/语音/贴纸；caption 可保留。
- 群/频道资料头像仅是选择器 UI 例外，不进入 JSON。
- JSON 是权威数据源。

## 3. tgctl / Codex 长期安全边界

`tgctl` 的架构必须保持：

```text
Codex
→ 本地 tgctl
→ 共享 TelegramService
→ 共享 TG Exporter Session / proxy
→ Telethon user account
```

不得复制 Telegram 登录系统。CLI 必须继续复用：

```text
%APPDATA%\TelegramMultiChatExporter\api_credentials.json
%APPDATA%\TelegramMultiChatExporter\telegram.session
```

以及现有 Windows system proxy detection。

如果 Session 未授权，CLI 只返回 `NOT_AUTHORIZED` 并提示先打开 TG Exporter 登录；不得在 tgctl 里重新做 phone / OTP / 2FA 交互登录。

读取类操作可直接执行：

```text
status
chats list
messages search
messages get
```

写入类操作当前只有：

```text
forward
send
```

规则：

- `forward` 必须使用 Telegram 真正 forward，不能静默退化为复制正文 + send。
- `send` 第一版只做纯文本。
- forward/send 必须支持 `--dry-run`。
- forward 默认最多 20 条；`--allow-large-batch` 后最多 200 条；不要移除这个闸门或把默认提高到危险值。
- FloodWait 不疯狂自动重试；返回结构化等待秒数。
- 同名/模糊 chat 不得静默选择；必须返回 `AMBIGUOUS_CHAT` 和候选 chat_id。
- 核心命令 `--json` stdout 必须只输出 JSON envelope；日志不得混入 stdout。
- 写操作日志只记录动作、chat_id、message_id/数量和结果，**不得记录聊天正文**。
- **未来 Agent 不得擅自让 Codex 写操作绕过 dry-run/批量上限/歧义检查/FloodWait/Session lock 等安全边界。**
- 不得增加自动规则转发、24/7 listener、群管理、删除消息、联系人管理、管理员操作等能力，除非用户重新明确提出并重新评估安全设计。

## 4. Shared Session 进程所有权

Telethon 默认 SQLiteSession 不应由 GUI 与 CLI 两个进程同时打开。

v0.1.9 起 `TelegramService` 自身拥有 Session OS lock，因此所有复用该 Service 的入口自动受保护。

第一版约束：

- GUI 与 tgctl 不能同时拥有同一 Session；
- 后启动者得到 `SessionBusyError` / `SESSION_BUSY`；
- 不得为了“方便并发”绕过 lock、复制 Session 或创建隐藏的第二 Session；
- 未来若要 GUI + CLI + MCP 并发，应采用单一 Telegram daemon 持有 Session，其他客户端走 IPC。

本版不要提前实现 daemon/MCP。

## 5. 群组工作区、Telegram 分组与导出分类

- 完整账号列表只作为 catalogue；主 GUI 只显示 focused workspace。
- 已选群 ID 保存在 `settings.json`。
- Telegram Chat Folders / Dialog Filters 只读，用于筛选 catalogue。
- Export Category 是本地落盘分类，保存在 `export_categories` / `group_export_categories`。
- 内置 `未分类` 作为兜底。
- 群头像按需加载、受限并发、本地缓存；失败不得阻断功能。
- `tgctl chats list` 应复用同一 catalogue / Chat Folder / migration collapse，不再造第二套群读取逻辑。

## 6. Basic Group → Supergroup

从 v0.1.8 起：

- 旧 Basic Group 和当前 Supergroup 不得同时作为两条 catalogue row。
- 当前 Supergroup 是主实体；不得删除/退出/修改真实超级群。
- legacy peer id 保存在 `migrated_from_chat_id`。
- current unread / since-last 只针对当前 Supergroup。
- GUI date-range 可读取 legacy + current 并按时间合并。
- tgctl catalogue 同样只能暴露当前逻辑群，不能重新扩大重复群问题。
- 不按“同名”猜 migration，只依赖 Telegram 显式迁移关系。

## 7. 未读与已读策略

current unread 使用刷新 catalogue 时冻结的：

```text
read_inbox_max_id < message_id <= latest_message_id_at_refresh
```

GUI Option B `导出后标已读`：默认 OFF，仅 current unread 可用。

严格顺序：

```text
JSON 原子写入成功
→ checkpoint 更新
→ 可选 read acknowledgement
```

导出失败绝不改变 read marker；read ack 失败不删除 JSON。

本版 tgctl 不需要提供 mark-read；未来若增加，必须重新遵守明确 write-operation 安全边界。

## 8. qasync / GUI

Telethon 与 Qt 共用 qasync 单事件循环。历史上 blocking modal API 导致 task re-entry。

- async slot 中不得重新引入 `QDialog.exec()`、static QMessageBox/QInputDialog 等 nested event loop。
- 使用现有 non-blocking dialog + await finished。
- 头像任务同一 asyncio/qasync loop。
- shutdown 必须兼容 Telethon `disconnect()` 返回 awaitable 或同步完成。
- shutdown 清理失败不得变成 PyInstaller 顶层 fatal dialog。
- tgctl 不依赖 Qt，不得为了 CLI 把 Qt 引进 Telegram Core。

## 9. 网络、Secret 与日志

- Windows system proxy 显式传给 Telethon。
- 兼容目录固定 `%APPDATA%\TelegramMultiChatExporter\`，不要因品牌变化迁移。
- 严禁提交/打印：api_hash、phone、OTP/code、2FA、Session 内容、真实聊天正文、真实头像 cache。
- `local_state.json` 只存 checkpoint。
- CLI `messages search/get` 的正文可以作为用户明确请求的 stdout 数据，但**不得进入普通日志**。
- 新增 debug 日志前先确认对象 `repr()` 不会泄露敏感字段。

## 10. Telegram Desktop JSON

GUI 导出仍以纯文本范围内尽量兼容 Telegram Desktop 为目标，不做完整媒体备份。已知差异继续维护在 `docs/JSON_COMPATIBILITY.md`。

tgctl 的 JSON 是独立的机器调用协议，不要求伪装成 Telegram Desktop export JSON；它必须保持稳定 envelope/error code。

## 11. 当前明确不做

除非用户再次明确提出：

- MCP Server；
- Web Server / 云端服务；
- Telegram Bot API / bot account；
- 长期监听；
- 自动转发规则引擎；
- AI 分类器；
- 消息媒体下载/媒体发送/媒体转发；
- 联系人/群/管理员管理；
- 删除消息；
- 360/杀软误报、自动白名单、代码签名。

## 12. Git / CI / Release

默认流程：最新 main → 功能分支 → tests → PR → Windows CI → CI 全绿 → 合并 → 用户可见二进制变化发 Release。

不得强推 main，不得把失败 CI 留给用户，不得把 Actions Artifact 当正式长期下载。

v0.1.9+ 最低 CI：

```text
pytest -q
GUI + tgctl import check
TGExporter PyInstaller build
TGExporter packaged smoke-test
tgctl PyInstaller build
tgctl packaged smoke-test
```

Release 还必须：

```text
TGExporter one-file
TGExporter portable
portable 内 tgctl.exe
standalone tgctl.exe
全部 packaged smoke-test
SHA256SUMS
GitHub Release upload
```

真实 Telegram 写操作不能由 CI 替代，必须在 HANDOFF 明确哪些仅 mock、哪些用户已 E2E。

## 13. 交接纪律

用户可见功能、关键 bug、架构、安全策略、Release 或真人 E2E 状态改变后必须更新 `HANDOFF.md`；长期决策同时更新 `docs/DECISIONS.md`。

合格交接必须能回答：最新版、main 未发布状态、哪些已真人验证、哪些仅 CI、当前安全边界、下一步优先事项。
