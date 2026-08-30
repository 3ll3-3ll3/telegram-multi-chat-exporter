# AGENTS.md

本文件是任何后续 Agent / Codex / 自动化开发者进入本仓库后的第一阅读入口。除非用户明确改变产品方向，否则以下规则视为长期不变量。

## 1. 接手顺序

新 Agent 在修改代码前必须依次阅读并核对：

1. `AGENTS.md`
2. `HANDOFF.md`
3. `README.md`
4. `docs/KNOWN_ISSUES.md`
5. `docs/ARCHITECTURE.md`
6. `docs/SECURITY_MODEL.md` + `SECURITY.md`
7. `docs/TESTING.md`
8. `docs/DEPLOYMENT.md`
9. `docs/RELEASE_PROCESS.md`
10. 与当前任务有关的 `docs/decisions/` ADR
11. GitHub 当前 main / Issues / PRs / Actions / Latest Release

在恢复完成前不要修改代码。GitHub 当前事实与文档冲突时，以 GitHub 为准，并先修正文档。

## 2. 当前产品代际

```text
v0.1.x = GUI exporter + direct-session tgctl
v0.2.0 = single daemon + Windows Named Pipe IPC
v0.3.0 = v0.2 daemon + Personal Account Reader
```

当前正式 Production：**v0.3.0**，tag/target commit `8e230e33ea928bcf71296e4e5379b097446dbec5`。

正式发布只能来自 GitHub Release workflow；Actions Artifact 不是 Production。

## 3. Session / daemon 不变量

v0.3 架构必须保持：

```text
TGExporter GUI ─┐
               ├→ authenticated local Named Pipe / UTF-8 JSON → TG daemon → Telethon → one user Session
tgctl / Codex ─┘
```

- daemon 是唯一 TelegramClient / SQLite Session owner；
- GUI/tgctl 不得 fallback direct-open Session，不复制 Session，不制造第二隐藏 Session；
- IPC 使用 Windows Named Pipe / `AF_PIPE` + UTF-8 JSON bytes，不用 pickle，不开 TCP/HTTP/Web；
- legacy/direct process 已持有 SessionLease 时才返回 `SESSION_BUSY`；packaged native exit code 必须保持 8；
- phone/OTP/2FA 只在 GUI；tgctl/Codex 不增加登录交互。

## 4. GUI 导出不变量

- 每群每次导出独立 JSON；历史 JSON 不读取、不合并、不回写、不覆盖；
- 输出：`output_root / Export Category / group / YYYY-MM-DD_HH-mm-ss.json`，同秒 `_2/_3/...`；
- Export Category 是本地分类，不是 Telegram Chat Folder；
- 每群独立 date range / current unread / since last successful export；
- GUI 消息导出默认只保留 text/caption，不下载聊天媒体；群头像只是 selector UI cache；
- Basic Group→Supergroup catalogue 只显示 current logical group；legacy peer 只用于历史兼容，不按同名猜 migration；
- qasync async flow 禁止重新引入 `QDialog.exec()` 等 nested blocking modal；
- 兼容数据目录永久保持 `%APPDATA%\TelegramMultiChatExporter\`。

### Current unread

每个群必须在该群真正开始执行 current-unread 导出时单独冻结：

```text
lower = read_inbox_max_id_at_group_start
upper = latest_message_id_at_group_start
export only lower < id <= upper
```

不得退回 catalogue-refresh snapshot，也不得移除 upper bound。snapshot 后新消息不属于本次导出，也不得被本次 optional read-ack 标已读。Option B 默认 OFF，顺序严格：`JSON atomic success → checkpoint → optional read ack`，ack 只能推进到同一个 frozen upper。迁移群 current-unread 只使用 current logical Supergroup。

## 5. Reader 安全边界

默认 Reader 是 Telegram read-only：account/dialog/chat/member/history/search/get/topic/media metadata 读取不得发送、转发、删除、退群、改 Folder、标已读或自动下载媒体。

显式 `media download` 是本地磁盘副作用，必须 plan → confirmation token → download；normal 20 files / 500 MiB，显式 large 最大 200 files / 5 GiB；`.part` 成功后 atomic rename。

现有 Telegram 写能力只包括已批准的 true-forward、plain-text send、GUI optional read-ack。不得因为 Reader 扩展而自动增加写权限。

## 6. Reader / identity / pagination

- Reader 使用独立模型，不把 private/bot/Saved Messages 强塞进 GUI `GroupInfo`；
- page default 100 / max 500；禁止无界 `limit=None`；
- cursor 必须 opaque/HMAC/query-bound，不含 access_hash/file_reference/credential；
- dialogs stable order；history newest→older；migration current→legacy；唯一定位 `(source_chat_id,message_id)`；
- owner/admin/member 是查询时 current snapshot，不伪造历史管理员任期；
- anonymous admin/send-as 不根据显示名、`post_author` 或管理员表反推隐藏个人；
- URL domain 必须解析真实 hostname，不做字符串 contains；
- 查不到消息保持 `MESSAGE_NOT_FOUND/not_found_or_unavailable`，不得伪造 deleted=true。

## 7. tgctl 写安全

- `forward` 必须是真实 Telegram forward；`send` 只做纯文本；
- forward/send 保留 `--dry-run`；forward 默认 20，显式 large 后 hard cap 200；
- 同名 dialog 返回 `AMBIGUOUS_CHAT`，不得 first-match；
- FloodWait 结构化停止，不 retry storm；
- 请求已交给 daemon 后 transport 中断，不自动 retry，返回 `WRITE_OUTCOME_UNKNOWN`；
- export 活跃时 real send/forward 立即 `EXPORT_IN_PROGRESS`，不得排队后偷偷执行。

## 8. Secret / 日志

严禁提交、普通日志、cursor、异常 repr 泄露：api_id/api_hash、phone、OTP/2FA、Session/credentials、access_hash、file_reference、IPC secret、真实导出正文。

用户明确执行 history/search/get 时正文可出现在 stdout JSON/JSONL；普通 `app.log` 不记录 message body/caption/URL text/media filename。写日志只记 action、安全 ID、数量、耗时/结果。

## 9. 明确非目标

除非用户重新授权并重新设计安全边界，不做：Secret Chat、删除内容恢复、绕权读取、Bot API 替代、24/7 listener、自动转发规则、AI 自动回复/自动分类、联系人/群/管理员管理、删除消息、退群、修改 Chat Folder、媒体发送/媒体转发、Web/TCP 服务。MCP 仍是未来可选方向，不属于 v0.3.0。

## 10. Git / CI / Release 纪律

- 不直接乱改 main，不 force-push；功能走 Issue/Branch/PR/CI/Review/Merge；
- 不删除/覆盖历史 tag/Release；
- 用户可见 runtime 修改至少跑 `pytest -q`、import gate、Windows one-file/portable/tgctl build、standalone+portable `SESSION_BUSY=8`、packaged smoke；
- 正式 Release 必须由 `.github/workflows/release.yml` 从 main 构建；
- 只有在 workflow success 且 GitHub Release 实体、tag target、assets、hash 均实际核验后，才能声称版本已发布；
- 真人 Telegram 副作用测试只在用户明确授权的安全目标上执行。

## 11. 交接纪律

任何正式 Release、架构、安全策略、关键 bug、Candidate/E2E 状态变化后更新 `HANDOFF.md`。长期不可逆决策同步 `docs/DECISIONS.md` 或独立 ADR。不要把聊天日志机械复制进仓库，只保存高度压缩、可恢复的项目事实。
