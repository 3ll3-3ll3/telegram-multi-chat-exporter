# HANDOFF.md

> 当前开发交接快照。任何 Agent 接手前先读 `AGENTS.md`，再读本文件。

更新时间：2026-08-30

## 1. 正式线

当前正式 Release：**TG Exporter v0.1.10**。

- merge commit：`cedb02035597aa607fac399666154519f480c431`
- Release workflow：`33287327783` success
- v0.1.10 修复 packaged `tgctl` 在部分 Windows 非 UTF-8 控制台输出中文 JSON 时可能 `UnicodeEncodeError`，导致 `SESSION_BUSY` native exit 1 而不是 8。
- v0.1.9 真人 E2E 已确认核心 read/export/真实 Saved Messages send/forward 和主要安全边界可用。

正式 Release 不受当前 v0.3 分支影响。

## 2. 代际与保留分支

```text
第一代 v0.1.x = GUI exporter + direct-session tgctl
第二代 v0.2.0 = single daemon + local IPC
第三代 v0.3.0 = v0.2 daemon + Personal Account Reader
```

第二代必须保留：

```text
codex/single-daemon-v0.2.0
base/head at v0.3 fork time = 165b0a86c85049cb25ab51f601c210ef986556a2
```

第三代设计 PR：`#19 docs: design v0.3.0 personal account reader`，base 是 v0.2.0 分支。

第三代实现分支：

```text
codex/personal-account-reader-v0.3.0
VERSION = v0.3.0
```

当前是 **candidate 开发线，不是正式 Release**。

## 3. 第二代体验已继承

v0.3 继续保持用户确认的 1B/2A/3B/4B/5B/6B/7A/8B：

- 关闭 GUI 时活跃 export job 后台继续；
- tgctl/Codex 可按需自动唤醒 daemon；
- export 活跃时 Telegram read 等待；
- export 活跃时真实 send/forward `EXPORT_IN_PROGRESS`，不偷偷排队发送；
- GUI 崩溃后 daemon/job 继续，重开可恢复状态；
- daemon 有 Windows tray；
- phone/OTP/2FA 仅 GUI；
- 空闲约 10 分钟 daemon 退出。

v0.3 GUI 与 v0.3 tgctl 都走 daemon，所以正常并行存在时**不应 `SESSION_BUSY`**。只有 legacy/direct process OS-lock 同一 Session 时才返回 `SESSION_BUSY`；packaged native exit 必须严格为 8。

## 4. v0.3 已实现 reader 能力

当前实现已包括：

```text
tgctl account get

tgctl dialogs list

tgctl chats get
tgctl chats members

tgctl messages history
tgctl messages search   # v3 advanced/global/paged
tgctl messages get      # v3 rich schema；--legacy-schema 兼容旧结果

tgctl topics list
tgctl topics history

tgctl media download    # plan -> confirmation token -> explicit download
```

Reader 独立模型：

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

GUI `GroupInfo` 没有被 private/bot/Saved Messages 污染。

## 5. dialogs / pagination

- dialogs 覆盖 group/supergroup/channel/private/bot/Saved Messages/archive/forum/unread/pinned/muted/folder/migration safe metadata。
- Saved Messages 使用唯一 self row `reference=me`。
- 默认 page 100，max 500。
- Cursor：base64url + HMAC-SHA256 + method/query fingerprint；不含 `access_hash` / `file_reference`。
- dialogs completeness 使用 canonical stable ordering，避免活跃度变化造成重复/遗漏。
- invalid/tamper/query mismatch → `INVALID_CURSOR`；无法恢复 Telegram offset entity → `CURSOR_STALE`。

## 6. members / roles / sender

- owner/admin/member 来自 Telegram participant/admin data。
- role 是查询时 current snapshot，不伪造历史管理员任期。
- role 不可见时 unknown/unavailable，不把 unknown 强制当 member。
- anonymous admin / send-as 不从显示名或 `post_author` 反推个人。
- migration legacy history 的 role snapshot 固定回当前逻辑群，不拿 legacy Basic Group 错当当前 Supergroup。

## 7. MessageInfoV3

history/search/get/topic history 统一趋向：

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

查不到消息继续 `MESSAGE_NOT_FOUND/not_found_or_unavailable`，不武断声称已删除。

Migration logical history：current → legacy，唯一定位键 `(source_chat_id, message_id)`。

## 8. advanced search

支持：single chat / global、contains、sender-id、sender-role、since/until、message type、topic、has-link、URL domain、cursor、limit、JSON/JSONL。

- bounded candidate scan，不为凑满结果无限扫描整个账号；
- `--url-domain` 解析 hostname；`mypikpak.com.evil.com` 不匹配 `mypikpak.com`；
- 不主动访问 URL、不 follow redirect。

## 9. Forum

使用 Telethon 1.44 的 `functions.messages.GetForumTopicsRequest(peer=...)`；不是旧/错误的 channels namespace。

- `topics list` bounded pagination；
- `topics history` 复用 MessageInfoV3 history；
- 非 Forum → `NOT_A_FORUM`。

## 10. media

消息读取默认 metadata-only，不下载。

显式 `media download`：

1. 用户必须给 `--output`；
2. 第一次只读取所选消息 metadata，返回 `DOWNLOAD_CONFIRMATION_REQUIRED`、file_count、known estimated bytes、unknown size count、confirmation token；**不创建输出目录、不下载**；
3. token 绑定 chat/ids/output/allow-large + plan digest，短时有效；
4. 第二次 `--confirm <token>` 才下载；
5. 普通限制 20 files / 500 MiB；`--allow-large-download` 后最大 200 files / 5 GiB；
6. 实际未知大小文件下载时继续按实际累计 bytes hard cap；
7. `.part` → 成功后 `os.replace`，失败/取消清理当前 `.part`；
8. 文件名做 Windows/path traversal 安全化，不允许 media filename 逃出 output dir。

Ctrl+C CLI exit 130；已确认的 daemon-side bounded download 可安全 detach，最终文件不会以半写 `.part` 冒充成功文件。

## 11. JSON/JSONL / exit codes

JSON envelope 保持：

```json
{"ok":true,"data":{}}
{"ok":false,"error":{"code":"...","message":"...","details":{}}}
```

Reader JSONL：meta → item* → end；错误单行 error。

新增 exit code：

```text
INVALID_CURSOR / CURSOR_STALE = 12
ACCESS_DENIED / MEMBERS_UNAVAILABLE = 13
NOT_A_FORUM = 14
DOWNLOAD_CONFIRMATION_REQUIRED = 15
DOWNLOAD_LIMIT_EXCEEDED = 16
```

历史 `SESSION_BUSY = 8` 不变。

## 12. 安全边界

reader 默认 Telegram read-only：不发送、不转发、不删除、不退群、不改 Chat Folder、不标已读、不自动下载媒体。

现有 send/forward/GUI optional read-ack 仍保留但不扩权。

禁止 stdout/log/cursor 暴露：api_id/api_hash、phone、OTP/2FA、Session、credentials 原文、access_hash、file_reference、IPC secret。

消息正文只在用户明确 reader stdout JSON/JSONL 中出现；普通 app.log 不记录正文/caption/URL 文本/媒体文件名。

## 13. 测试状态

已完成并曾全绿的基础 v0.3 Windows CI head 包含：

- pytest；
- GUI + tgctl/reader import；
- TGExporter PyInstaller；
- tgctl PyInstaller；
- packaged smoke。

后续已继续加入：advanced search、Forum、media、v0.1.10 packaged `SESSION_BUSY exit=8` regression。最新 head 必须重新完整跑绿后才能称 candidate ready。

已新增测试覆盖：cursor query binding/tamper、all dialog types、Saved Messages、bounded pagination、rich history/media metadata、JSONL、URL lookalike domain、search continuation、Forum Telethon API contract、media plan/confirm/limits/atomic file。

Mock/CI **不能替代**真实账号只读 E2E。

## 14. 仍待完成的 Phase G

在宣布 candidate ready 前必须：

1. 最新 head Windows CI 全绿，包括 packaged SESSION_BUSY native exit 8；
2. 更新 README/AGENTS/HANDOFF/CODEX_TGCTL/ARCHITECTURE/SECURITY/TESTING/release notes；
3. 创建以 v0.2.0 为 base 的 v0.3 implementation PR；
4. PR CI 全绿；
5. 生成 candidate EXEs artifact 并记录 SHA-256；
6. 真实账号只读 E2E：dialogs types、Svip 500 history、owner/admin、pikpak/mypikpak sender、structured sender、anonymous admin、pagination、since/until、Saved Messages、MESSAGE_NOT_FOUND、AMBIGUOUS_CHAT、GUI+tgctl coexist、legacy lock→SESSION_BUSY 8、FloodWait（自然/mock）、logs、Forum if available、metadata-only no download。

本环境不能替代用户真实 Telegram 账号；如果无法在 GitHub Actions 做真人 E2E，必须明确标记待用户本机执行。

## 15. 发布闸门

完成代码、自动测试、Windows candidate 与可完成的只读 E2E 准备后**停止**：

- 不 merge release commit；
- 不创建/覆盖 `v0.3.0` GitHub Release；
- 不改 v0.1.10 tag/assets；
- 等用户本地验收和明确“发布 v0.3.0”授权。
