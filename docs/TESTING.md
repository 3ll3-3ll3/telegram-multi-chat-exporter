# Testing Guide

本项目测试分三层：

1. CI/unit/mock：模型、GUI 导出、tgctl parser/protocol/safety、PyInstaller。
2. packaged smoke-test：TGExporter.exe / tgctl.exe 能启动 smoke path。
3. 真实 Telegram E2E：登录、folders、read marker、migration、真实 search/forward/send。

CI green 不等于真实账号 E2E。

## 1. 本地/CI 基线

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
```

v0.1.9+ 最低 PR 门槛：

```text
pytest -q
GUI + tgctl import check
TGExporter one-file build
TGExporter packaged --smoke-test
tgctl one-file build
tgctl packaged --smoke-test
```

正式 Release 还必须验证 GUI portable，并确认 portable 内 `tgctl.exe` 也能 smoke-test。

## 2. GUI 回归矩阵

至少保持：

- 首次 GUI 登录与 Session 复用；
- Windows system proxy / Clash；
- qasync non-blocking login/dialog；
- focused workspace；
- Telegram Chat Folder；
- avatar lazy load；
- Export Category create/persist/delete-without-disk-delete；
- `category/group/timestamp.json`；
- same-second no overwrite；
- Basic Group → Supergroup catalogue collapse；
- migrated date-range legacy + current history；
- frozen current unread；
- Option B read ack order；
- since-last monotonic checkpoint；
- shutdown no `await None` fatal dialog。

用户已在 v0.1.8 对分类目录、migration collapse/history 与旧 Session/settings 兼容完成真人验证。

## 3. tgctl unit tests

`tests/test_tgctl.py` 至少覆盖：

```text
CLI 参数解析
--json success envelope
structured failure/error code
chat not found
ambiguous title -> candidates
search contains/since/until/limit
messages get missing ids
forward dry-run no write
send dry-run no write
write logs do not contain message body
20 default forward limit
200 allow-large hard cap
NOT_AUTHORIZED
FloodWait -> retry_after_seconds
safe status/output excludes credential fields
```

`tests/test_session_lock.py` 覆盖 SessionLease 基本生命周期。

所有 Telegram API 实际 write unit tests 使用 Fake/Mock client；CI 不连接用户账号。

## 4. JSON stdout test

`--json` 模式必须：

- stdout 只有一份 JSON；
- 不含 logging 前缀；
- success 为 `{"ok":true,"data":...}`；
- failure 为 `{"ok":false,"error":...}`；
- exit code 0/非0 与结果匹配。

stderr 可以用于人类模式错误，但 JSON 模式不得要求 Codex 解析日志判断成功失败。

## 5. Chat resolution tests

允许：marked chat_id、精确 @username、精确 title。

必须测：

- 单一精确 title 成功；
- 两个相同 title → `AMBIGUOUS_CHAT`；
- details 包含候选 chat_id/title/username/type；
- numeric id 不存在 → `CHAT_NOT_FOUND`；
- 不 first-match。

`chats list` 继续复用 migration-collapsed catalogue，不能重新显示 legacy Basic Group duplicate。

## 6. Search tests

第一版 deterministic filter：

```text
chat
contains
since inclusive
until exclusive
limit
case_sensitive optional
```

测试 text/caption 范围；不下载媒体。

时间无 tz 的 CLI parser 按本机 timezone 解释；aware datetime 原样使用。

## 7. Write safety tests

### forward dry-run

- 完成 source/destination resolution；
- 检查 ids；
- 不调用 `client.forward_messages`；
- 返回 requested/successful/failed ids；
- `--to me` 可解析 Saved Messages。

### real forward mock

- 必须调用 Telethon `forward_messages`；
- 不能改为复制 text + `send_message`；
- media message first version 不真正 forward，进入 failed_ids。

### send dry-run

- 不调用 `send_message`；
- stdout 可回显用户明确提供的 dry-run text；
- app.log 不含 body。

### real send mock

- `parse_mode=None`；
- 不附加 media/file；
- 返回 sent message id。

### limits

```text
20 条：默认允许
21 条：默认 INVALID_ARGUMENT
21 条 + --allow-large-batch：允许
200 条 + flag：允许
201 条 + flag：拒绝
```

## 8. FloodWait

mock `FloodWaitError`，预期：

```json
{
  "ok": false,
  "error": {
    "code": "FLOOD_WAIT",
    "details": {"retry_after_seconds": 37}
  }
}
```

不得自动循环 retry。真实账号 E2E 不要故意制造 FloodWait。

## 9. Session ownership / concurrency

第一版 Telethon SQLiteSession 由 `SessionLease` 保证单进程所有权。

真人 E2E：

1. 打开 TG Exporter GUI 并连接。
2. 另一个 shell 执行 `tgctl status --json`。
3. 预期 `SESSION_BUSY`，无 SQLite corruption。
4. 关闭 GUI。
5. tgctl 再执行应正常获得 Session。
6. 反向：让一个 tgctl 操作占用 Session 时启动 GUI，应得到友好 busy 提示。

不要通过删除 lock file 测试解锁；真正 ownership 来自 OS lock。

## 10. tgctl 真实账号 E2E

先确保 v0.1.8 GUI 已登录并关闭 GUI。

只读：

```powershell
tgctl status --json
tgctl chats list --search "保研" --json
tgctl chats list --folder "保研" --json
tgctl messages search --chat <chat_id> --contains "预推免" --limit 20 --json
tgctl messages get --chat <chat_id> --ids <message_id> --json
```

检查：无需 phone/OTP/2FA；chat_id/title 正确；文本来自真实消息；无媒体下载。

## 11. 真实 Telegram 写操作 E2E

只有用户明确确认后执行，优先 Saved Messages。

先 dry-run：

```powershell
tgctl forward --from <chat_id> --to me --ids <message_id> --dry-run --json
tgctl send --to me --text "TG Exporter Codex bridge test" --dry-run --json
```

确认 Telegram 没产生新消息。

用户确认后真实写：

```powershell
tgctl forward --from <chat_id> --to me --ids <message_id> --json
tgctl send --to me --text "TG Exporter Codex bridge test" --json
```

检查 Saved Messages：

- forward 是真正 forward（保留 Telegram 转发来源语义）；
- send 是纯文本；
- 返回 JSON ids 与实际一致。

不要自行向陌生人/陌生群测试。

## 12. Security tests

仓库/CI/app.log 不得出现：

```text
api_hash
phone
OTP/code
2FA
.session contents
message body
avatar bytes
```

特别测试 send/forward 日志：正文字符串不能出现在 `caplog`。

`status` 不输出 phone；只允许 user id/display name/username/session safe label/proxy safe label。

## 13. Release validation

正式 v0.1.9+ Release 必须包含：

```text
TGExporter-vX.Y.Z-windows-x64.exe
TGExporter-vX.Y.Z-windows-x64-portable.zip
tgctl.exe
SHA256SUMS.txt
```

Portable ZIP 内必须存在：

```text
TGExporter/TGExporter.exe
TGExporter/tgctl.exe
```

Release workflow 必须完成：

```text
pytest
GUI + tgctl import
GUI one-file build
GUI portable build
tgctl build
GUI one-file smoke
GUI portable smoke
tgctl standalone smoke
portable tgctl smoke
SHA256SUMS
Release upload
```

Release 后核对 tag/target/draft/prerelease/assets/hashes。

## 14. Future MCP tests

当前不做 MCP。如果未来实现，必须新增 daemon ownership、IPC auth、tool schema、write confirmation、crash recovery 测试；不得让 MCP 绕过 tgctl 已建立的 write safety invariants。
