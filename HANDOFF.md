# HANDOFF.md

> 当前开发交接快照。任何 Agent 接手前先读 `AGENTS.md`，再读本文件。

更新时间：2026-08-30

## 1. 正式线

当前正式 Release：**TG Exporter v0.1.10**。

- main / Release target：`cedb02035597aa607fac399666154519f480c431`
- v0.1.10 修复 Windows packaged `tgctl` 在非 UTF-8 console/redirect 环境中输出中文 JSON 时可能触发 `UnicodeEncodeError`，导致 `SESSION_BUSY` native exit 1 而不是 8。
- v0.1.9 真人 E2E 已确认 GUI 导出、Session 复用、reader 基础命令、真实 Saved Messages send/forward 与主要安全边界可用。

正式 v0.1.10 不受第三代 candidate 分支影响。

## 2. 三代关系

```text
第一代 v0.1.x = GUI exporter + direct-session tgctl
第二代 v0.2.0 = single daemon + Windows Named Pipe IPC
第三代 v0.3.0 = v0.2 daemon + Personal Account Reader
```

第二代保留分支：

```text
codex/single-daemon-v0.2.0
base/head at v0.3 fork time = 165b0a86c85049cb25ab51f601c210ef986556a2
```

第三代：

```text
branch: codex/personal-account-reader-v0.3.0
PR: #20 feat: v0.3.0 personal account reader candidate
VERSION: v0.3.0
```

PR #20 当前故意以 `codex/single-daemon-v0.2.0` 为 base，用于第三代 candidate 验证；它不是正式发布 PR，仍保持 Draft，不得在真人验收前 merge / Release。

## 3. v0.3 已继承的 daemon 体验

v0.3 继续保持第二代已确定的桌面行为：

- daemon 是唯一 TelegramClient / Session owner；
- GUI 和 tgctl 都走本地 authenticated Named Pipe，不再各自 direct-open SQLiteSession；
- GUI 关闭/崩溃时活跃 export job 可继续；
- tgctl/Codex 可按需自动唤醒 daemon；
- export 活跃时 Telegram reader 等待；
- export 活跃时真实 send/forward 立即 `EXPORT_IN_PROGRESS`，不得排队后偷偷发送；
- daemon 有 Windows tray；
- phone/OTP/2FA 只在 GUI；
- 空闲约 10 分钟 daemon 退出；
- v0.3 GUI + v0.3 tgctl 正常共存时不应 `SESSION_BUSY`；只有 legacy/direct Session holder 才触发 `SESSION_BUSY`。

Packaged `SESSION_BUSY` native exit code 契约保持为 **8**。

## 4. v0.3 已实现 Reader 命令

```text
tgctl account get

tgctl dialogs list

tgctl chats get
tgctl chats members

tgctl messages history
tgctl messages search
tgctl messages get

tgctl topics list
tgctl topics history

tgctl media download
```

旧命令 `status/chats list/messages search/messages get/forward/send` 继续兼容；rich search/get 有 legacy schema 过渡。

Reader 使用独立模型，不把 private/bot/Saved Messages 强塞进 GUI `GroupInfo`：

```text
AccountProfile
DialogInfo
ChatDetails
ParticipantInfo
SenderInfo
MessageInfoV3
ForumTopicInfo
MediaMetadata
Page
```

## 5. Dialogs / pagination / migration

- dialogs 覆盖 group/supergroup/channel/private/bot/Saved Messages/archive/forum/unread/pinned/muted/folder/migration safe metadata；
- Saved Messages 唯一 self row：`reference=me`；
- default page 100，max 500；
- cursor = base64url + HMAC-SHA256 + method/query fingerprint；不得含 access_hash/file_reference/credential；
- dialogs 使用 canonical stable ordering；
- history newest → older；
- Basic Group→Supergroup logical history = current → legacy composite cursor；
- migration 消息唯一键必须是 `(source_chat_id,message_id)`。

## 6. Members / sender / Rich MessageInfoV3

- owner/admin/member 来自 Telegram participant/admin data；
- role 是查询时 current snapshot，不伪造历史管理员任期；
- unknown role 不强制写成 member；
- anonymous admin / send-as 不从显示名、`post_author` 或管理员列表反推隐藏个人；
- migration legacy history 的 role snapshot 仍基于当前逻辑群。

Rich schema 覆盖：

```text
chat_id / source_chat_id / message_id
date / edit_date
structured sender
text / caption
entities
reply_to_message_id / reply_to_top_id
forum_topic_id
forward_origin
grouped_id
views / forwards
reactions
poll
service_action
pinned
media metadata
availability
```

查不到消息保持 `MESSAGE_NOT_FOUND / not_found_or_unavailable`，不得武断声称“已删除”。

## 7. Advanced search / Forum

Search 支持：single/global、contains、sender-id、sender-role、since/until、message-type、topic、has-link、URL domain、cursor、limit、JSON/JSONL。

- bounded candidate scan，不为凑满结果无限扫描整个账号；
- `--url-domain` 使用真实 hostname parsing；`mypikpak.com.evil.com` 不匹配 `mypikpak.com`；
- 不访问 URL、不 follow redirect。

Forum 使用 Telethon 1.44：

```text
functions.messages.GetForumTopicsRequest(peer=...)
```

非 Forum 返回 `NOT_A_FORUM`。

## 8. Media

普通 history/search/get 默认 **metadata-only**，不下载。

显式 `media download`：

1. 用户必须给 output；
2. 第一次只 plan，返回 `DOWNLOAD_CONFIRMATION_REQUIRED` + file_count/estimated_bytes/unknown_size_count/token；不创建 output dir、不下载；
3. token 绑定 chat/ids/output/allow-large + plan digest，短时有效；
4. 第二次 `--confirm` 才下载；
5. normal 20 files / 500 MiB；explicit large 最大 200 files / 5 GiB；
6. 未知大小下载继续按实际累计 bytes 执行 hard cap；
7. `.part` → 成功后 `os.replace`；失败/取消清理当前 `.part`；
8. 文件名做 Windows/path traversal 安全化。

Ctrl+C CLI exit 130；已确认的 daemon-side bounded download 可安全 detach，半写 `.part` 不得冒充成功文件。

## 9. JSON / JSONL / exit codes

JSON envelope：

```json
{"ok":true,"data":{}}
{"ok":false,"error":{"code":"...","message":"...","details":{}}}
```

Reader JSONL：meta → item* → end；错误为单行 error。

关键 exit code：

```text
SESSION_BUSY = 8
EXPORT_IN_PROGRESS = 9
WRITE_OUTCOME_UNKNOWN = 10
DAEMON_UNAVAILABLE = 11
INVALID_CURSOR / CURSOR_STALE = 12
ACCESS_DENIED / MEMBERS_UNAVAILABLE = 13
NOT_A_FORUM = 14
DOWNLOAD_CONFIRMATION_REQUIRED = 15
DOWNLOAD_LIMIT_EXCEEDED = 16
Ctrl+C = 130
```

## 10. 安全边界

Reader 默认 Telegram read-only：不发送、不转发、不删除、不退群、不改 Chat Folder、不标已读、不自动下载媒体。

既有 send/forward/GUI optional read-ack 仍保留但不扩权：

- true forward；
- plain-text send / `parse_mode=None`；
- dry-run；
- forward 默认 20、显式 large 最大 200；
- AMBIGUOUS_CHAT 不 first-match；
- FloodWait 返回等待秒数，不 retry storm；
- write 已发送但响应前 transport 中断 → `WRITE_OUTCOME_UNKNOWN`，不自动 retry；
- export 活跃时 real write → `EXPORT_IN_PROGRESS`。

严禁普通 log/stdout/cursor 非授权泄露：api_id/api_hash、phone、OTP/2FA、Session/credentials、access_hash、file_reference、IPC secret。消息正文仅在用户明确 reader stdout JSON/JSONL 中允许；普通 app.log 不记录正文/caption/URL text/media filename。

## 11. Candidate 自动化状态

PR #20 在 runtime candidate head `dede883b6eb0306fe44ed7751f5bebd9d1cf3e21` 上的 Windows PR CI：

```text
run 33291856851 = success
pytest = 85 passed
GUI + reader import = success
TGExporter PyInstaller = success
tgctl PyInstaller = success
real OS Session lock -> packaged SESSION_BUSY + native exit 8 = success
TGExporter/tgctl packaged smoke = success
artifact upload = success
```

该 run 生成的 candidate：

```text
artifact id: 9726241546
artifact name: TGExporter-v0.3.0-candidate-windows-x64
artifact zip digest: 970b403037a6fe95fee7e46e106e83e6501243fa132b32a9434acc7932735091
TGExporter.exe: cea25ce0022fb517933e24029d7fc167050b7260a60ec3c653c1ccdd54a32ffd
tgctl.exe: 6e46597689a24281089cfba827b0755414b00698c5b9471d3566374b5286e25a
```

**注意：上述 artifact 对应 runtime head `dede...`。** 2026-08-30 真人 E2E 前尾部审查又补了 Release workflow / handoff 等非业务收尾；新的 branch head 必须再次 Windows CI 全绿后，优先使用新 artifact 做真人验收。

## 12. 2026-08-30 尾部审查结论与已修项

真人验收前复核发现并处理：

1. v0.3 branch 的正式 `.github/workflows/release.yml` 曾遗漏 v0.1.10 已有的 **standalone + portable packaged `SESSION_BUSY` JSON/native exit 8 gate**；已 forward-port；
2. 正式 Release import check 已扩大到 daemon + reader + tgctl，而不是只检查旧 GUI/CLI import；
3. 本 HANDOFF 原先把“更新 docs / 创建 implementation PR / PR CI / candidate artifact”等已完成事项仍列为 pending；已纠正。

仍故意保持：

- PR #20 Draft；
- 不 merge；
- 不创建/覆盖 v0.3.0 Release；
- `docs/releases/v0.3.0.md` 仍写 Candidate/未发布，正式发布授权后再改为最终 Release Notes。

## 13. 真人 E2E 现在真正剩余的项目

CI/mock 不能替代以下用户本机只读验收：

1. all dialogs：group/supergroup/channel/private/bot/Saved/archive；
2. Telegram Chat Folder membership；
3. 真实聊天最近 500 history；
4. owner/admin；
5. sender / sender-role / pikpak + real mypikpak.com domain；
6. anonymous admin/send-as 不误归属；
7. history 多页无 overlap/gap；
8. since/until；
9. Saved Messages history/search；
10. MESSAGE_NOT_FOUND；
11. AMBIGUOUS_CHAT；
12. v0.3 GUI + tgctl coexist；
13. legacy direct Session lock → packaged SESSION_BUSY + native exit 8；
14. legacy lock 下 GUI safe diagnostic，无 `database is locked`；
15. FloodWait 仅自然出现时观察，不故意制造；
16. logs/stdout safety；
17. Forum（若账号有条件）；
18. media metadata-only 不产生文件；
19. media plan 第一次不创建目录/不下载；
20. media confirm 真下载仅在用户明确选择时测试。

默认真人 E2E 不执行 send/forward/mark-read，也不需要真实媒体下载。

## 14. 真人验收通过后的正式集成路径

这是一个重要发布纪律：**不要把 PR #20 直接 merge 到它当前的 v0.2 base 后就声称 v0.3 已进入 main。**

PR #20 当前 base 是 `codex/single-daemon-v0.2.0`，而正式线是 `main @ v0.1.10`。真人 E2E 通过后必须先完成最终正式线集成：

```text
用户 E2E PASS
→ 把 v0.2 + v0.3 完整实现集成/retarget 到最新 main（必须保留 v0.1.10 ancestry/行为）
→ 解决任何 integration conflict
→ 再跑完整 Windows PR CI / packaged gates
→ 确认集成没有改变已验收 runtime 语义
→ 将 docs/releases/v0.3.0.md 从 Candidate Notes 收尾为正式 Release Notes
→ 用户明确授权“发布 v0.3.0”
→ release: v0.3.0 进入 main
→ formal Release workflow
→ 验证 one-file / portable / tgctl / SHA256 / Release target
→ 更新 HANDOFF 为正式版状态
```

若最终集成产生业务代码变化，必须针对受影响功能补做 E2E；不能拿集成前的真人结果替代集成后代码。

## 15. 当前唯一合理下一步

等待当前尾部收尾 head 的 Windows CI 全绿并生成新的 candidate artifact，然后交给用户做 **真实 Telegram 账号只读 E2E**。

在此之前不要继续堆新功能，不要 merge，不要 Release。
