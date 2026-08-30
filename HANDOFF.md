# HANDOFF.md

> 当前开发交接快照。任何 Agent 接手前先读 `AGENTS.md`，再读本文件。

更新时间：2026-08-30

## 1. 正式线 / 版本映射

当前正式线已经到 **TG Exporter v0.1.10**。

- v0.1.10 merge commit：`cedb02035597aa607fac399666154519f480c431`
- v0.1.10 Release workflow：`33287327783` success
- v0.1.10 是 v0.1.9 的 packaged tgctl UTF-8 / `SESSION_BUSY` exit-code hotfix。
- v0.1.9 真人 E2E 已确认核心 read/export/real Saved Messages send/forward 与主要安全边界可用；发现的 packaged `SESSION_BUSY` exit=1 根因已在 v0.1.10 修复。
- 本设计分支没有重新抄录 v0.1.10 最终 asset SHA-256；需要时从正式 Release / `SHA256SUMS.txt` 核对，不得猜。

本项目后续把“产品第几代”和仓库版本统一映射：

```text
第一代 = v0.1.x  GUI exporter + tgctl direct-session
第二代 = v0.2.0  single daemon + local IPC
第三代 = v0.3.0  daemon + Personal Account Reader
```

用户新提示词里写的“v0.1.9 → v0.2.0 personal reader”属于另一套版本叙述；在本仓库中必须解释为 **v0.3.0**，不能覆盖现有 v0.2.0。

## 2. 第二代 v0.2.0 必须完整保留

现有实现分支：

```text
codex/single-daemon-v0.2.0
head = 165b0a86c85049cb25ab51f601c210ef986556a2
```

用户明确要求“2.0 先保存着”，因此：

- 不改名；
- 不 force-push；
- 不用 v0.3 设计覆盖它；
- v0.3 从它的架构继续演进。

该分支相对当前 main（v0.1.10）已经 diverged：v0.2.0 有大量 daemon 实现，但缺 main 上 v0.1.10 的一条 UTF-8 packaged tgctl hotfix。未来 v0.3 实施必须 forward-port v0.1.10 fix/test；不要通过回退 daemon 来解决。

## 3. v0.2.0 已确认的桌面体验继续作为 v0.3 基础

用户已经确认：

- **1B**：关闭 GUI 时，正在导出的 job 继续后台完成。
- **2A**：GUI 没开时，Codex/tgctl 自动唤醒 daemon。
- **3B**：导出期间 Telegram read 等待导出结束，不与导出并发。
- **4B**：导出期间真正 send/forward 禁止执行，返回 `EXPORT_IN_PROGRESS`；不得排队后偷偷发送。
- **5B**：GUI 崩溃后 daemon/job 继续；重开 GUI 恢复 job 进度/结果。
- **6B**：daemon 有 Windows 托盘图标，可看状态并请求退出。
- **7A**：phone/OTP/2FA 仍只在 GUI；tgctl/Codex 不登录。
- **8B**：无 GUI lease、无 job、无请求/排队 read 后约 10 分钟 idle exit；下次自动唤醒。

v0.3 不得反转这些选择。

## 4. v0.2.0 当前架构不变量

```text
TG daemon（唯一 Session/Telethon owner）
├─ TG Exporter GUI IPC client
├─ tgctl IPC client
└─ future MCP IPC client（v0.3 仍不实现 MCP）
```

必须继续：

1. 只有 daemon 创建 `TelegramClient` / 获取 `SessionLease`。
2. GUI/tgctl 不 direct-open SQLiteSession，不 fallback direct Session。
3. IPC：Windows Named Pipe / `AF_PIPE` + UTF-8 JSON bytes；禁止 pickle object transport；不开 TCP/HTTP。
4. IPC identity/auth secret 只在本地 AppData，secret 不日志、不 stdout、不 Git。
5. GUI export daemon-side 执行并原子写 JSON。
6. `JSON success → checkpoint → optional read ack` 仍由 daemon coordinator 保证。
7. export 独占 Telegram work；read 等待；真实 write 拒绝。
8. write transport outcome unknown 不自动 retry。
9. daemon 按需启动、托盘可见、idle shutdown。
10. daemon 不做 Windows Service/开机自启/24x7 Telegram listener/自动规则/MCP。

详细第二代设计：`docs/DAEMON_IPC_DESIGN.md`。

## 5. 第三代 v0.3.0 设计状态

纯设计分支：

```text
design/personal-account-reader-v0.3.0
base = codex/single-daemon-v0.2.0 @ 165b0a86c85049cb25ab51f601c210ef986556a2
```

主设计文档：

```text
docs/PERSONAL_ACCOUNT_READER_V3_DESIGN.md
```

长期决策：

```text
docs/DECISIONS.md D-033 ~ D-043
```

当前阶段只设计，不改运行代码，不 bump VERSION，不发布 Release。

## 6. v0.3.0 产品目标

目标不是制作 Telegram 客户端，而是让本地 Codex 只通过 tgctl 可靠回答：

```text
我的账号加入了哪些会话？
某群群主和管理员是谁？
某人或当前某角色在指定时间内发过什么？
最近 500 条中谁发过 PikPak / mypikpak.com 链接？
某条消息回复了谁、转发自哪里？
某个 Forum Topic 中有哪些消息？
我的 Saved Messages 中有哪些匹配内容？
```

默认全部 reader 命令是 Telegram read-only：不发送、不转发、不删除、不退群、不改 Chat Folder、不标已读、不自动下载媒体。

现有 send/forward/GUI Option B 不删除，但不得因为 reader 新能力扩大授权范围。

## 7. v0.3.0 新能力范围

计划新增：

```text
tgctl account get

tgctl dialogs list

tgctl chats get
tgctl chats members

tgctl messages history
tgctl messages search   # 扩展，全局/单 chat、sender role/domain/topic/type/cursor
tgctl messages get      # 升级到统一 rich schema

tgctl topics list
tgctl topics history

tgctl media download    # 默认先 plan，第二次确认后才写本地文件
```

完整 dialogs 覆盖：

- group / supergroup / channel；
- private；
- bot；
- Saved Messages；
- archive；
- Telegram Chat Folder；
- forum / unread / pinned / muted / migration metadata。

## 8. Reader 模型与 GUI 隔离

不要把 private/bot/Saved Messages 机械塞进现有 GUI `GroupInfo`。

新增 reader-only：

```text
AccountProfile
DialogInfo
ChatDetails
ParticipantInfo
SenderInfo
MessageInfoV3
ForumTopicInfo
MediaMetadata
Page[T]
```

GUI `GroupInfo/chats.catalogue` 继续现有导出器语义，降低 GUI regression 风险。

## 9. 分页与 cursor

统一：

```text
default page = 100
max page = 500
```

全历史不允许无上限读取。

Cursor：

- opaque base64url；
- HMAC integrity；
- 绑定 method + query fingerprint；
- payload 只含安全 offset / marked peer id / segment；
- 不含 `access_hash` / `file_reference`；
- invalid/tamper → `INVALID_CURSOR`；
- entity offset 无法恢复 → `CURSOR_STALE`。

Dialogs 为稳定 completeness 默认 canonical order `(dialog_type_rank, marked_chat_id)`，避免新消息改变 Telegram activity order 导致分页重复/遗漏。

Messages history newest→older，以 message id 继续。

Migration logical history：current supergroup segment → legacy basic group segment；唯一定位键 `(source_chat_id,message_id)`。

## 10. Sender / role 语义

不再只返回 sender 显示名。

统一 sender fields：

```text
sender_id
sender_type=user|chat|channel|anonymous_admin|unknown
display_name
username
posted_as_chat_id
is_creator
is_admin
admin_title
anonymous_admin
via_bot_id
role_basis
```

重要：owner/admin/member 默认是 **查询时当前角色**，不是历史发送时角色。Telegram 不提供完整管理员任期，禁止伪造历史 role。

匿名管理员/send-as 不能根据显示名、`post_author`、管理员名单反推出具体 user id。

## 11. MessageInfoV3

history/search/get/topic history 统一：

```text
chat_id
source_chat_id
message_id
date/edit_date
sender
text/caption
entities
reply_to_message_id/reply_to_top_id
forum_topic_id
forward_origin
grouped_id
views/forwards
reactions
poll
service_action
pinned
media metadata
availability
```

Telegram 不会把已删除历史作为普通 row 返回，因此不得伪造 `deleted=true`；查不到继续 `MESSAGE_NOT_FOUND/not_found_or_unavailable`。

## 12. 搜索要求

`messages search` 扩展支持：

- 单 chat / global；
- contains；
- sender-id；
- sender-role；
- since/until；
- message type；
- forum topic；
- has-link；
- URL domain；
- cursor/limit；
- JSON/JSONL。

`--url-domain mypikpak.com` 必须解析真实 hostname，匹配 exact host/subdomain；`mypikpak.com.evil.test` 不匹配。不 follow redirect、不访问链接。

全局 sender-role 为 chat-relative：每个命中 chat 按需取 current role snapshot；role 不可见则 unknown，unknown 不得当 member。

## 13. 媒体策略

默认只返回：

```text
media_type
filename
mime_type
size
dimensions
duration
document_id/photo_id
```

不下载，不返回 `file_reference`。

显式 `tgctl media download` 必须：

1. 提供 output directory；
2. 第一次只 plan 数量/预计大小并返回 confirmation token；
3. 第二次带 token 才下载；
4. 普通/large/hard cap；
5. `.part` 临时文件 → 成功 atomic rename；
6. Ctrl+C/取消不留下伪装成功的最终文件。

## 14. v0.3.0 SESSION_BUSY 验收修正

**不能照抄旧提示词的“GUI 占 Session → tgctl busy”。**

v0.3 正确语义：

```text
v0.3 GUI + v0.3 tgctl 同时用
→ 共用 daemon
→ 正常，不应 SESSION_BUSY
```

只有 legacy/direct process 占着 SessionLease：

```text
daemon acquire fail
→ SESSION_BUSY
→ packaged native exit 8
```

v0.1.10 console UTF-8 fix/test 必须 forward-port 到 v0.3。

## 15. v0.3.0 实施阶段（尚未开始）

建议未来实现分支：

```text
codex/personal-account-reader-v0.3.0
```

顺序：

### Phase A
safe models + cursor + JSONL + forward-port v0.1.10 UTF-8 hotfix。

### Phase B
account + all dialogs + Saved Messages + generic dialog resolution。

### Phase C
chat details + participants + owner/admin/member + role cache。

### Phase D
MessageInfoV3 + history + migration composite cursor。

### Phase E
advanced search + URL domain + forum topics。

### Phase F
explicit media download plan/confirm/cancel。

### Phase G
Windows package + real account read-only E2E + candidate hashes。

完成 Phase G 后 **停止，不发布 Release**，等待用户本地验收和明确发布授权。

## 16. 真实账号 E2E 核心标准

必须只读验证：

- all dialog types，包括 private/bot/Saved/archive；
- 真实群最近 500 history；
- owner/admin；
- `pikpak` sender；
- 真实 `mypikpak.com` domain sender；
- sender structured identity；
- anonymous admin 不误归属；
- history 翻页无重复/遗漏；
- since inclusive / until exclusive；
- Saved Messages history/search；
- MESSAGE_NOT_FOUND；
- AMBIGUOUS_CHAT；
- v0.3 GUI + tgctl coexist；
- legacy lock → SESSION_BUSY exit 8；
- FloodWait structured/no retry storm；
- logs/output sensitive allowlist；
- forum（若账号有可用真实 forum）；
- media metadata-only 不生成下载文件。

Mock 不能替代真人只读 E2E。

## 17. 历史规则仍保持

- GUI 输出：`总目录 / Export Category / 群组 / YYYY-MM-DD_HH-mm-ss.json`；历史 JSON 不合并。
- GUI 聊天消息不下载媒体；头像只是 UI cache。
- migrated Basic Group GUI 只显示当前 Supergroup；date-range 可读取 legacy+current。
- current unread frozen snapshot。
- Option B 默认 OFF：JSON success → checkpoint → optional read ack。
- Qt/qasync 不重新引入 nested blocking modal。
- 日志严禁 api_hash/phone/OTP/2FA/Session/message body/access_hash/file_reference。

## 18. 当前工作边界

当前仅完成 **v0.3.0 设计**。

- 不修改 v0.2.0 分支；
- 不实现 reader runtime；
- 不 bump VERSION；
- 不开正式 v0.3 Release；
- 后续只有用户明确要求“开始实现 v3”时才创建实现分支并写代码。
