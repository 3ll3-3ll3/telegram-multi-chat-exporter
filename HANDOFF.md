# HANDOFF.md

> 当前开发交接快照。任何 Agent 接手前先读 `AGENTS.md`，再读本文件。

更新时间：2026-08-30

## 1. 正式线

当前正式 Release：**TG Exporter v0.1.10**。

- `main` / Release target：`cedb02035597aa607fac399666154519f480c431`
- v0.1.10 修复 Windows packaged `tgctl` 在非 UTF-8 console/redirect 环境中输出中文 JSON 时可能触发 `UnicodeEncodeError`，导致 `SESSION_BUSY` native exit 1 而不是 8。
- 第三代 candidate 已在真人 E2E 前把 `main@v0.1.10` 纳入 ancestry；PR #20 现在直接以 `main` 为 base。

正式 v0.1.10 仍不受 candidate 分支影响；未经用户明确授权，不 merge、不创建/覆盖 v0.3.0 Release。

## 2. 三代关系与当前 PR

```text
第一代 v0.1.x = GUI exporter + direct-session tgctl
第二代 v0.2.0 = single daemon + Windows Named Pipe IPC
第三代 v0.3.0 = v0.2 daemon + Personal Account Reader
```

第二代保留分支：

```text
codex/single-daemon-v0.2.0
fork-time head = 165b0a86c85049cb25ab51f601c210ef986556a2
```

第三代：

```text
branch: codex/personal-account-reader-v0.3.0
PR: #20 feat: v0.3.0 personal account reader candidate
base: main
VERSION: v0.3.0
state: OPEN + DRAFT
```

PR #20 已完成正式线提前整合，当前可 merge 但**故意保持 Draft**。真人验收前不得 merge / Release。

## 3. v0.3 daemon 基线

- daemon 是唯一 TelegramClient / Session owner；
- GUI 和 tgctl 都走本地 authenticated Named Pipe，不再各自 direct-open SQLiteSession；
- GUI 关闭/崩溃时活跃 export job 可继续；
- tgctl/Codex 可按需唤醒 daemon；
- export 活跃时 Telegram reader 等待；
- export 活跃时真实 send/forward 立即 `EXPORT_IN_PROGRESS`，不得排队后偷偷发送；
- daemon 有 Windows tray；
- phone/OTP/2FA 只在 GUI；
- 空闲约 10 分钟 daemon 退出；
- v0.3 GUI + v0.3 tgctl 正常共存不应 `SESSION_BUSY`；legacy/direct Session holder 才触发 `SESSION_BUSY`。

Packaged `SESSION_BUSY` native exit code 契约保持为 **8**。

## 4. v0.3 Reader 命令

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

Reader 使用独立模型：`AccountProfile / DialogInfo / ChatDetails / ParticipantInfo / SenderInfo / MessageInfoV3 / ForumTopicInfo / MediaMetadata / Page`。

## 5. Dialogs / pagination / migration

- dialogs 覆盖 group/supergroup/channel/private/bot/Saved Messages/archive/forum/unread/pinned/muted/folder/migration safe metadata；
- Saved Messages 唯一 self row：`reference=me`；
- default page 100，max 500；
- cursor = base64url + HMAC-SHA256 + method/query fingerprint；不得含 access_hash/file_reference/credential；
- dialogs canonical stable order；history newest → older；
- Basic Group→Supergroup logical history = current → legacy composite cursor；
- migration 消息唯一键为 `(source_chat_id,message_id)`；
- global advanced search 已修复 legacy segment cursor 被忽略导致重复/遗漏的问题；
- single-chat migrated search 会校验 cursor segment；迁移关系丢失时返回 `CURSOR_STALE`；
- rich `messages get` 从 legacy source 读取时保持：`chat_id=current logical supergroup`、`source_chat_id=legacy basic group`。

## 6. Members / sender / Rich MessageInfoV3

- owner/admin/member 来自 Telegram participant/admin data；
- role 是查询时 current snapshot，不伪造历史管理员任期；
- unknown role 不强制写成 member；
- anonymous admin / send-as 不从显示名、`post_author` 或管理员列表反推隐藏个人；
- migration legacy history 的 role snapshot 始终基于当前逻辑 Supergroup entity。

Rich schema 覆盖 sender、reply、forum topic、forward origin、entities、views/forwards、reactions、poll、service action、pinned、media metadata、availability。

查不到消息保持 `MESSAGE_NOT_FOUND / not_found_or_unavailable`，不得武断声称“已删除”。

## 7. Advanced search / Forum

Search 支持 single/global、contains、sender-id、sender-role、since/until、message-type、topic、has-link、URL domain、cursor、limit、JSON/JSONL。

- bounded candidate scan，不为凑满结果无限扫描整个账号；
- `--url-domain` 使用真实 hostname parsing；`mypikpak.com.evil.com` 不匹配 `mypikpak.com`；
- 不访问 URL、不 follow redirect。

Forum 使用 Telethon 1.44：`functions.messages.GetForumTopicsRequest(peer=...)`；非 Forum 返回 `NOT_A_FORUM`。

## 8. Media

普通 history/search/get 默认 **metadata-only**，不下载。

显式 `media download`：

1. 必须显式指定 output；
2. 第一次只 plan，返回 `DOWNLOAD_CONFIRMATION_REQUIRED`，不创建 output dir、不下载；
3. token 绑定 chat/ids/output/allow-large + plan digest，短时有效；
4. 第二次 `--confirm` 才下载；
5. normal 20 files / 500 MiB；explicit large 最大 200 files / 5 GiB；
6. 未知大小按实际累计 bytes 执行 hard cap；
7. `.part` → 成功后 `os.replace`；失败/取消清理当前 `.part`；
8. 文件名做 Windows/path traversal 安全化。

Ctrl+C CLI exit 130；已确认的 daemon-side bounded download 可安全 detach，半写 `.part` 不得冒充成功文件。

## 9. JSON / JSONL / exit codes

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

Reader JSONL：`meta → item* → end`；错误为单行 error。

## 10. 安全边界

Reader 默认 Telegram read-only：不发送、不转发、不删除、不退群、不改 Chat Folder、不标已读、不自动下载媒体。

既有 send/forward/GUI optional read-ack 仍保留但不扩权：true forward、plain-text send / `parse_mode=None`、dry-run、forward 20/200 cap、AMBIGUOUS_CHAT 不 first-match、FloodWait structured stop、`WRITE_OUTCOME_UNKNOWN` 不 retry、export 活跃时 real write 拒绝。

严禁普通 log/stdout/cursor 非授权泄露：api_id/api_hash、phone、OTP/2FA、Session/credentials、access_hash、file_reference、IPC secret。消息正文仅在用户明确 reader stdout JSON/JSONL 中允许；普通 app.log 不记录正文/caption/URL text/media filename。

## 11. 真人验收前尾部审计已修项

2026-08-30 发布前复核实际发现并处理：

1. 正式 `.github/workflows/release.yml` 曾遗漏 v0.1.10 的 standalone + portable packaged `SESSION_BUSY` JSON/native exit 8 gate；已恢复；
2. 正式 Release import gate 已扩大到 daemon + reader + tgctl；
3. v0.1.10 cp1252/UTF-8 source regression、Session lock helper、v0.1.10 release history 已完整保留；
4. global migrated advanced-search legacy pagination bug 已修复并有回归测试；
5. single-chat migrated search cursor segment / stale 语义已加固；
6. migrated history 管理员角色必须使用 current logical Supergroup entity，已有回归测试；
7. migrated rich-get 的 logical/source chat identity 已统一并有回归测试；
8. Candidate gate 从仅 one-file 扩大到 one-file + portable；
9. `main@v0.1.10` 已在真人 E2E 前纳入 candidate ancestry，PR #20 已 retarget 到 `main`；
10. PR #20 当前无 review submission、无未解决 inline review thread。

## 12. Frozen 真人 E2E Candidate

为了保证“验收的二进制”固定且可追溯，真人验收使用以下 **frozen runtime candidate**。后续纯文档提交不替换该二进制，也不改变其运行代码。

```text
runtime head: 0ad4219ef367d28326b5aca705fffe1d007db52b
Windows PR CI run: 33293667296 = success
pytest: 91 passed
import gate: GUI + daemon + reader + CLI = success
one-file TGExporter build = success
portable TGExporter build = success
standalone tgctl build = success
standalone SESSION_BUSY JSON + native exit 8 = success
portable SESSION_BUSY JSON + native exit 8 = success
one-file GUI smoke = success
portable GUI smoke = success
standalone tgctl smoke = success
portable tgctl smoke = success
artifact upload = success
```

Candidate artifact：

```text
artifact id: 9726786295
artifact name: TGExporter-v0.3.0-candidate-windows-x64
artifact outer ZIP digest: 37309a137577f8aa3de63bc5ff2a188147b1908be5d4e7a0e53df531358503f7

TGExporter-v0.3.0-candidate-windows-x64.exe
SHA-256: 94f43dadc421e67de0a5f8cb7d1ff0b3f98bb85e46a46ca423c9d7d025fc55c6

TGExporter-v0.3.0-candidate-windows-x64-portable.zip
SHA-256: 6d0dad9514eab1ff1c4d80b35df704951fc7fe63ff23bea2536dcf01c19626bc

tgctl.exe
SHA-256: aee8edbe9c7693b3fa299757bc386b285c42003e03d787718903b7223ae638a0
```

Artifact URL：`https://github.com/3ll3-3ll3/tg-exporter/actions/runs/33293667296/artifacts/9726786295`

## 13. 真人 E2E 待验证

CI/mock 不能替代以下用户本机验收：

1. all dialogs：group/supergroup/channel/private/bot/Saved/archive；
2. Telegram Chat Folder membership；
3. 真实聊天最近 500 history；
4. owner/admin；
5. sender / sender-role / real domain search；
6. anonymous admin/send-as 不误归属；
7. history/search 多页无 overlap/gap；
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

## 14. 真人验收通过后的发布路径

正式线整合已经提前完成，因此不再需要“验收后先把 v0.2/v0.3 再整合到 main”的高风险步骤。

```text
用户 E2E PASS
→ 如 E2E 未引发业务代码修改，确认 PR #20 仍 mergeable / checks 正常
→ 将 docs/releases/v0.3.0.md 从 Candidate Notes 收尾为正式 Release Notes
→ 用户明确授权“发布 v0.3.0”
→ release: v0.3.0 进入 main
→ formal Release workflow
→ 验证 one-file / portable / tgctl / SHA256 / Release target
→ 更新 HANDOFF 为正式版状态
```

若真人 E2E 导致任何业务代码变化，必须针对受影响功能重新跑 Windows CI，并对受影响真实场景补做 E2E。

## 15. 当前唯一合理下一步

**交用户进行真实 Telegram 账号 E2E。**

在真人验收结论出来前，不继续堆新功能，不 merge，不 Release。
