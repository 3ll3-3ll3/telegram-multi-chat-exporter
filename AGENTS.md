# AGENTS.md

本文件是任何后续 Agent / Codex / 自动化开发者进入本仓库后的**第一阅读入口**。除非用户明确改变产品方向，否则以下规则视为长期不变量。

## 1. 开工前必须完成的恢复流程

在修改任何代码、Workflow、Release 或用户本机数据之前，按顺序完成：

1. 读 `AGENTS.md`；
2. 读 `HANDOFF.md`；
3. 读 `README.md`；
4. 读 `docs/ARCHITECTURE.md`；
5. 读 `docs/SECURITY_MODEL.md` 和根目录 `SECURITY.md`；
6. 读 `docs/TESTING.md`、`docs/DEPLOYMENT.md`、`docs/RELEASE_PROCESS.md`；
7. 涉及当前 v0.3 工作时，读 PR #20 及其分支中的 `docs/PERSONAL_ACCOUNT_READER_V3_DESIGN.md`、`docs/DAEMON_IPC_DESIGN.md`；
8. 读与当前任务相关的 `docs/decisions/` ADR；
9. 核对默认分支、当前开发分支、最新 commit、open PR、CI、Release/Tag；
10. 在确认仓库事实与 `HANDOFF.md` 一致前，不修改代码。

不要只凭 README、聊天记忆或旧分支判断当前状态。**GitHub 当前事实优先，`HANDOFF.md` 负责解释正式线与开发线之间的关系。**

## 2. 当前代际与状态发现规则

项目采用以下统一版本叙述：

```text
v0.1.x = 第一代：GUI exporter + direct-session tgctl
v0.2.0 = 第二代：single daemon + Windows Named Pipe IPC
v0.3.0 = 第三代：v0.2 daemon + Personal Account Reader
```

截至 2026-08-30：

- 正式 Production Release：`v0.1.10`；
- `main`：`cedb02035597aa607fac399666154519f480c431`；
- 当前实现开发线：`codex/personal-account-reader-v0.3.0`，Draft PR #20；
- PR #17 / #19 是历史设计 PR，不是当前实施入口；
- 当前第三代在真人 Telegram E2E 通过并获得用户明确发布授权前，不得 merge/release。

这些值会变化；每次接手必须重新核对 GitHub，并更新 `HANDOFF.md`。

## 3. Production 在本项目中的含义

本项目**没有远程生产数据库、云端生产服务或服务器部署**。

这里的 Production 指：

1. GitHub Releases 上已正式发布的 Windows 二进制；
2. 用户本机 `%APPDATA%\TelegramMultiChatExporter\` 中的真实 Telegram Session、API 配置、设置、checkpoint、日志和 cache；
3. 用户真实 Telegram 账号及其可见聊天。

因此“生产安全”主要是：不破坏正式 Release 历史、不泄露/损坏本机 Session、不擅自执行 Telegram write、不删除用户导出历史。

## 4. Git / PR / Release 纪律

仓库当前分支没有 GitHub branch protection，**所以 Agent 必须自行强制执行流程纪律**：

- 不直接把功能代码 push 到 `main`；
- 不 force-push `main`；
- 不移动、覆盖或删除历史 Release tag；
- 不覆盖已有 GitHub Release；
- 功能/修复：latest main → 独立分支 → tests → PR → Windows CI → 用户需要的真人 E2E → 明确发布授权 → merge/release；
- Actions Artifact 是临时候选，不是正式长期下载；正式用户资产只认 GitHub Release；
- CI 失败由开发 Agent 自己读取日志、修复、重跑，不把失败任务留给用户；
- 正式 Release 只有在 tag、target commit、assets、SHA256、workflow 全部核验后才能对用户宣称“已发布”。

## 5. 产品核心不变量

TG Exporter 是 Windows Telegram 文本导出器，并逐步增加 Codex 本地读取/操作接口；不是 Telegram Desktop 替代品、累计归档数据库、云服务或 Bot API 产品。

GUI 导出必须保持：

- 每群每次导出独立 JSON；历史 JSON 不读取、不合并、不覆盖；
- 输出结构：`总输出目录 / Export Category / 群组 / YYYY-MM-DD_HH-mm-ss.json`；同秒冲突 `_2/_3/...`；
- Export Category 是软件本地分类，不是 Telegram Chat Folder；分类不存在时软件自动建目录；
- 每群独立 date range / current unread / since last successful export；
- GUI 消息导出只保留文字/caption，不下载聊天媒体；群头像仅 selector UI cache 例外；
- Telegram Desktop JSON 只追求纯文本范围内兼容，不扩成完整媒体备份；
- `%APPDATA%\TelegramMultiChatExporter\` 是兼容路径，品牌改名也不得擅自迁移；
- 软件删除分类不得删除已有磁盘导出历史。

## 6. Basic Group → Supergroup

长期规则：

- catalogue 只显示当前 logical Supergroup；
- legacy Basic Group 只用于 migration/history 兼容；
- 不按同名猜 migration，只依据 Telegram 显式关系；
- 不删除、退出、降级或修改用户真实 Supergroup；
- current unread / since-last 只针对当前 Supergroup；
- date-range/history 可读取 current + legacy；
- 迁移历史的唯一定位键是 `(source_chat_id, message_id)`，不能只按 message id 去重；
- v0.3 rich history/search/get 对 legacy 消息仍应保持 `chat_id=current logical supergroup`、`source_chat_id=legacy basic group`；
- owner/admin/member current snapshot 必须基于当前 logical chat，而不是 legacy peer。

## 7. current unread / read acknowledgement

current unread 使用冻结边界。GUI “导出后标已读”默认 OFF，只在 current-unread 模式可用。

顺序不可改变：

```text
JSON 原子写入成功
→ checkpoint 更新
→ 可选 Telegram read acknowledgement
```

导出失败绝不标已读；read ack 失败不删除已经成功的 JSON。

## 8. qasync / GUI 永久踩坑

Qt + Telethon 共享 qasync 单事件循环。历史上 blocking modal/nested event loop 导致 task re-entry。

- async flow 中不得重新引入 `QDialog.exec()`、static blocking QMessageBox/QInputDialog 等 nested modal；
- 继续使用 non-blocking dialog + await completion；
- shutdown 必须兼容 `disconnect()` 返回 awaitable 或同步完成；
- 清理失败不能变成 PyInstaller 顶层 fatal dialog；
- tgctl/Core 不应为了 CLI 被迫依赖 Qt。

## 9. v0.1.x tgctl 写安全

正式 v0.1.10 的 `tgctl` 继续遵守：

- 复用 GUI 已登录 Session，不做第二套 phone/OTP/2FA CLI 登录；
- `forward` 是 Telegram true forward，不能静默复制正文 + send；
- `send` 只发纯文本，`parse_mode=None`；
- forward/send 保留 `--dry-run`；
- forward 默认 <=20，显式 large 后 hard cap 200；
- 同名 chat → `AMBIGUOUS_CHAT`，不得 first-match；
- FloodWait 返回结构化等待秒数，不 retry storm；
- write log 不记录正文；
- packaged `SESSION_BUSY` JSON + native exit code 8 是回归契约。

v0.1.x direct GUI/tgctl 的 SessionLease 互斥属于正式版兼容语义，不要在 hotfix 中绕锁或复制 Session。

## 10. v0.2/v0.3 single-daemon 不变量

在 PR #20 / v0.3 线工作时，架构必须保持：

```text
TG daemon（唯一 TelegramService / Telethon / telegram.session owner）
├─ TG Exporter GUI IPC client
├─ tgctl IPC client
└─ future MCP client（当前不实现）
```

- GUI/tgctl 不得 fallback direct Session；
- IPC 使用 authenticated Windows Named Pipe / AF_PIPE + UTF-8 JSON bytes；禁止 pickle transport；不开 TCP/HTTP/Web Server；
- GUI 与同代 tgctl 正常共存，不应互相 `SESSION_BUSY`；`SESSION_BUSY` 只用于 legacy/direct process 已锁 Session 的兼容边界；
- GUI 关闭/崩溃时 daemon-side export 可继续；GUI 重开读取安全 job metadata；
- tgctl/Codex 可按需唤醒 daemon；无 GUI/job/request 后约 10 分钟 idle exit；
- daemon 有 Windows tray，但 tray 异常不能使后台功能失败；
- export 活跃时 Telegram reader 等待；真实 send/forward 立即 `EXPORT_IN_PROGRESS`，不得排队后偷偷发送；
- write 请求已交给 daemon 后 transport outcome unknown → `WRITE_OUTCOME_UNKNOWN`，绝不自动 retry；
- phone/OTP/2FA 仍只由 GUI 交互。

## 11. v0.3 Personal Account Reader 安全边界

Reader 默认 Telegram read-only：

```text
account get
dialogs list
chats get
chats members
messages history/search/get
topics list/history
media metadata
```

读取不得发送、转发、删除、退群、改 Chat Folder、投票、标已读或自动下载媒体。

Reader 使用独立模型，不把 private/bot/Saved Messages 强塞进 GUI `GroupInfo`。

分页：default 100 / max 500；不得提供隐藏的无界 history。Cursor 必须 opaque/HMAC/query-bound，不含 `access_hash`、`file_reference`、Session/credential。

owner/admin/member 是查询时 current snapshot；匿名管理员/send-as 不得从显示名、`post_author` 或管理员列表反推真实 user。

`--url-domain` 必须解析 hostname；`example.com.evil.test` 不得匹配 `example.com`，且不访问 URL、不 follow redirect。

显式 `media download` 是本地磁盘副作用：必须 plan → confirmation token → download；normal 20 files/500 MiB，explicit large hard cap 200 files/5 GiB；`.part` 成功后原子 rename。

## 12. Secret / 日志 / 本地数据

禁止提交、stdout（非用户明确 reader 结果）、普通日志、cursor、异常 repr 泄露：

- `api_id` / `api_hash`；
- phone / OTP / 2FA；
- `*.session`、session journal、credentials；
- Telegram `access_hash` / `file_reference`；
- IPC auth secret；
- 用户真实聊天正文、导出 JSON、头像 cache。

消息正文只有在用户明确执行 history/search/get 等 reader 命令时才允许出现在该命令 stdout JSON/JSONL；普通 `app.log` 不得记录正文、caption、URL 文本或媒体文件名。

不得通过删除 lock 文件、复制 Session、迁移 AppData 来“修复”并发问题。

## 13. 明确非目标 / 已否决方向

除非用户重新明确要求并重新进行安全设计，不做：

- MCP Server（future direction，不是 v0.3 范围）；
- Web/TCP server / 云端服务；
- Telegram Bot API / bot account；
- 24/7 listener；
- 自动转发规则 / AI 自主分类；
- 联系人、群、管理员管理；
- 删除消息、退群、修改 Chat Folder；
- Secret Chat / 已删除消息恢复 / 绕权读取；
- 媒体发送/媒体转发；
- 360/杀软误报、自动白名单、代码签名作为当前主线。

## 14. 测试与真人 E2E

CI 不能保存用户真实 Telegram credential，也不能替代真实账号 E2E。

代码变化至少按 `docs/TESTING.md` 执行；Windows binary 变化必须通过 PyInstaller/package smoke。涉及 Telegram write 的真人测试优先 Saved Messages，先 dry-run，再由用户明确确认；不要自行向陌生群/联系人发消息，不要故意制造 FloodWait。

v0.3 Candidate 当前发布闸门：真人只读 E2E 未完成前，不继续堆新功能、不 merge PR #20、不创建/覆盖 v0.3.0 Release。

## 15. 交接纪律

任何用户可见功能、关键 bug、架构、安全策略、正式 Release、Candidate、真人 E2E 状态变化后都必须更新 `HANDOFF.md`。

长期不可逆决策：优先写入 `docs/decisions/` ADR，并在 `docs/DECISIONS.md` 建索引。

一个合格的新对话恢复必须能仅凭仓库回答：当前正式版/commit、当前开发 branch/PR、当前任务、CI/E2E 状态、已知风险、安全禁区、下一步。