# HANDOFF.md

> 当前项目交接快照。任何新 Agent / GPT 接手时先读 `AGENTS.md`，再读本文件；完成恢复检查前不要修改代码。

# Current Project State

**Last updated:** 2026-08-30 13:36 +08:00  
**Repository:** `3ll3-3ll3/tg-exporter`  
**Default branch:** `main`  
**Current version under development:** `v0.3.0` Candidate  
**Production version:** `v0.1.10`  
**Production commit / tag:** `cedb02035597aa607fac399666154519f480c431` / `v0.1.10`  
**Current development branch:** `codex/personal-account-reader-v0.3.0`  
**Current development branch tip:** `7282326e3ce51a294b90840e9cf7c965ad304fc7`  
**Frozen runtime candidate commit for human E2E:** `0ad4219ef367d28326b5aca705fffe1d007db52b`  
**Current task:** 用户本机真实 Telegram 账号 v0.3 只读 E2E；测试前不再加功能  
**Related Issue:** 无独立 Issue；当前工作由 PR 驱动  
**Related PR:** Draft PR #20 `feat: v0.3.0 personal account reader candidate`  
**Current release gate:** PR #20 不 merge；不创建/覆盖 `v0.3.0` Release，直到真人 E2E PASS + 用户明确发布授权

## Source-of-truth warning

默认 `main` 是当前**正式生产线**，不是最新开发代码。v0.3 runtime、daemon、reader 代码目前都在 PR #20 分支。

历史设计 Draft PR：

- PR #17 `docs: design single Telegram daemon + local IPC`：v0.2 设计依据，已被实现线吸收；不是当前继续开发入口；
- PR #19 `docs: design v0.3.0 personal account reader`：v0.3 设计依据，已被 PR #20 实现；不是当前继续开发入口；
- PR #20：唯一当前实施/验收入口。

旧分支 `docs/agent-handoff` 也是历史分支，不是当前 handoff 主线。

# Project Summary

TG Exporter / TG 导出器是 Windows 本地 Telegram 工具：

1. GUI：按群独立导出文字/caption 到 JSON；
2. `tgctl`：供 Codex/命令行读取、搜索并在明确安全边界内执行 Telegram true forward / 纯文本 send；
3. v0.2/v0.3：通过单一后台 daemon 统一持有 Telegram Session；
4. v0.3 Personal Account Reader：让 Codex 可分页读取账号、全部 dialogs、成员/管理员、rich messages、Forum、Saved Messages 和 media metadata，并提供显式两阶段本地媒体下载。

本项目不是 Telegram Desktop 替代品，不是累计数据库，不是云服务，不是 Bot API 产品，也不是 24/7 自主 Telegram Agent。

# Production Definition

本项目没有远程生产数据库、云端服务或服务器环境。

“Production”指：

- GitHub Release 正式 Windows 二进制；
- 用户本机 `%APPDATA%\TelegramMultiChatExporter\` 下的真实 API 配置、Telegram Session、settings/checkpoint/log/cache；
- 用户真实 Telegram 账号。

因此不得把云数据库/迁移/Secret Manager 的惯例机械套进本项目。生产安全重点是 Release 历史、本地 Session/配置、导出文件与真实 Telegram write。

# Production Version

GitHub 当前正式 Latest Release：**v0.1.10**，target `cedb02035597aa607fac399666154519f480c431`。

Release page：`https://github.com/3ll3-3ll3/tg-exporter/releases/tag/v0.1.10`

正式资产 GitHub 当前 digest：

```text
TGExporter-v0.1.10-windows-x64.exe
sha256 b598aecdd7fcc3f5731ba955f7f02d8bd45ea47220f66a040bc20b64f4e410be

TGExporter-v0.1.10-windows-x64-portable.zip
sha256 113c6f8223d6f648571bf8ad3e86a1df1db2ad1e118bb2674e70f0031b0274dd

tgctl.exe
sha256 ebd6cd8898f51aa9e63a7efa6292a70df0afe15cd5efe99b7fc4be9bbf2f5efa
```

v0.1.10 修复了 packaged `tgctl` 在非 UTF-8 Windows console/redirect 下中文 JSON 触发 `UnicodeEncodeError`、导致 `SESSION_BUSY` 原应 exit 8 却退成 exit 1 的问题。该 UTF-8 修复与 packaged regression 已 forward-port 到 v0.3 candidate。

# Current Architecture

## Production v0.1.10

```text
TGExporter GUI ─┐
                ├─ direct TelegramService/Telethon → shared telegram.session
 tgctl.exe     ─┘
```

GUI 与 tgctl 通过 OS `SessionLease` 防止同时打开同一 Telethon SQLiteSession。后启动者安全返回 `SESSION_BUSY`；不得绕锁或复制 Session。

## Candidate v0.3.0

```text
TGExporter GUI ─┐
                ├→ authenticated Windows Named Pipe / JSON → TG daemon → TelegramService/Telethon → one Session
 tgctl / Codex ─┘
```

v0.3 daemon 是唯一 TelegramClient/Session owner。GUI 与同代 tgctl 正常可以共存；`SESSION_BUSY` 只表示旧 direct process/其它 legacy 进程已经锁住 Session。

Operation policy：

```text
LOCAL status/job/heartbeat       → immediate
export                           → exclusive Telegram job
reader                           → waits while export active
real send/forward during export  → EXPORT_IN_PROGRESS, never queued for later
confirmed media download         → bounded local-disk side effect
```

详细设计：PR #20 分支 `docs/DAEMON_IPC_DESIGN.md`、`docs/PERSONAL_ACCOUNT_READER_V3_DESIGN.md`。

# Core Product Invariants

- 输出：`总输出目录 / Export Category / 群组 / YYYY-MM-DD_HH-mm-ss.json`；同秒 `_2/_3/...`；
- 分类在软件里创建/持久化/自动建文件夹；不是 Telegram Chat Folder；删除分类不删历史磁盘文件；
- 每次/每群 JSON 独立，不读取/合并/覆盖历史；
- GUI 默认只导出文字/caption，不下载聊天媒体；群头像是 UI cache 例外；
- Basic Group → Supergroup catalogue 只显示当前 logical group；legacy 只用于历史；
- current unread 使用冻结边界；
- “导出后标已读”默认 OFF，严格 `JSON atomic success → checkpoint → optional read ack`；
- qasync async flow 禁止重新引入 blocking nested modal (`QDialog.exec()` 等)；
- 兼容数据目录始终 `%APPDATA%\TelegramMultiChatExporter\`；不要因品牌名迁移。

# Completed

## v0.1.x 已正式完成

- Windows GUI 多群独立 JSON 导出；
- focused workspace、Telegram Chat Folder、群头像 lazy load；
- Export Category 与 `category/group/timestamp.json`；
- Basic Group→Supergroup catalogue collapse + date-range legacy history；
- current unread / since-last / Option B read ack；
- Windows system proxy；
- qasync modal/shutdown 历史问题修复；
- `tgctl` status/chats/search/get/forward/send、JSON contract、dry-run、20/200 guard、AMBIGUOUS_CHAT、FloodWait；
- v0.1.9 真人真实 Telegram send/forward 到 Saved Messages 已跑通；
- v0.1.10 packaged UTF-8/exit-code hotfix 正式发布。

## v0.2 daemon 已实现并被 v0.3 继承

分支 `codex/single-daemon-v0.2.0 @ 165b0a86c85049cb25ab51f601c210ef986556a2`。

已实现 single daemon、Named Pipe IPC、GUI/tgctl client、tray、lease/heartbeat、daemon-side export job、operation coordinator、idle shutdown、安全 write scheduling。v0.2 未单独作为正式 Release 发布；v0.3 直接继承该实现。

## v0.3 Candidate 主体已实现

PR #20 已实现：

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

关键语义：

- dialogs 覆盖 group/supergroup/channel/private/bot/Saved Messages/archive/forum/folder safe metadata；
- reader 独立模型，不破坏 GUI GroupInfo；
- default page 100 / max 500；HMAC/query-bound cursor；
- Rich MessageInfoV3：sender/reply/forward/entities/reactions/poll/service/media metadata 等；
- sender-role 是 current snapshot；anonymous/send-as 不反推隐藏个人；
- migration history current→legacy，以 `(source_chat_id,message_id)` 唯一定位；
- URL domain 使用真实 hostname；
- Forum topics；
- media 默认 metadata-only；显式 download 采用 plan→confirmation token→download + hard cap + `.part` atomic rename；
- 普通日志不记录正文/credentials/access_hash/file_reference。

# Pre-E2E Tail Audit Completed

真人验收前已经额外做过一次发布尾部审计，并实际发现/修复：

1. v0.3 正式 Release workflow 曾漏掉 v0.1.10 standalone + portable `SESSION_BUSY JSON/native exit 8` gate；已恢复；
2. Release import gate 扩到 daemon + reader + tgctl；
3. v0.1.10 cp1252/UTF-8 source regression、Session lock helper、release history 已保留；
4. global advanced search 在 migrated legacy segment 分页时忽略 cursor、可能重复/遗漏的 bug 已修；
5. single-chat migrated search cursor segment/stale 语义已加固；
6. legacy history 管理员角色改为 current logical Supergroup snapshot；
7. rich `messages get` legacy source 的 logical/source IDs 已统一；
8. Candidate CI 扩大到 one-file + portable；
9. `main@v0.1.10` 已纳入 PR #20 ancestry，PR base 已 retarget 为 `main`；
10. PR #20 当前没有 review submission / unresolved inline thread。

# Frozen v0.3 Human-E2E Candidate

真人验收固定使用以下 runtime candidate，避免“测的不是最终集成代码”：

```text
runtime commit: 0ad4219ef367d28326b5aca705fffe1d007db52b
Windows PR CI: 33293667296 = success
pytest: 91 passed
artifact id: 9726786295
artifact URL: https://github.com/3ll3-3ll3/tg-exporter/actions/runs/33293667296/artifacts/9726786295
```

Candidate assets：

```text
TGExporter-v0.3.0-candidate-windows-x64.exe
sha256 94f43dadc421e67de0a5f8cb7d1ff0b3f98bb85e46a46ca423c9d7d025fc55c6

TGExporter-v0.3.0-candidate-windows-x64-portable.zip
sha256 6d0dad9514eab1ff1c4d80b35df704951fc7fe63ff23bea2536dcf01c19626bc

tgctl.exe
sha256 aee8edbe9c7693b3fa299757bc386b285c42003e03d787718903b7223ae638a0

outer Actions artifact ZIP digest
sha256 37309a137577f8aa3de63bc5ff2a188147b1908be5d4e7a0e53df531358503f7
```

其后的 PR branch tip `7282326e...` 只是 HANDOFF/Candidate Notes 文档收尾；该 tip 又完整跑了 Windows run `33294055220`，全部 success。它不改变上述 frozen runtime。

# In Progress

**唯一当前任务：用户真人 Telegram 账号 E2E。**

在 E2E 结论出来前：

- 不继续堆新功能；
- 不 merge PR #20；
- 不创建/覆盖 v0.3.0 Release；
- 不把 PR #17/#19 当实施入口；
- 不自行执行真实 send/forward/mark-read；
- 不为了测试故意制造 FloodWait。

# Pending

真人 E2E 至少覆盖：

1. all dialogs：group/supergroup/channel/private/bot/Saved/archive；
2. Telegram Chat Folder membership；
3. 真实聊天最近 500 history；
4. owner/admin；
5. sender-id / current sender-role / real domain filter；
6. anonymous admin/send-as 不误归属；
7. history/search 多页无 overlap/gap；
8. since/until；
9. Saved Messages history/search；
10. `MESSAGE_NOT_FOUND`；
11. `AMBIGUOUS_CHAT`；
12. v0.3 GUI + tgctl coexist；
13. legacy direct Session lock → packaged `SESSION_BUSY` + native exit 8；
14. legacy lock 下 GUI safe diagnostic，无 `database is locked`；
15. logs/stdout safety；
16. Forum（账号有条件时）；
17. media metadata-only 不产生文件；
18. media plan 第一次不创建目录/不下载；
19. 真实 media confirm download 仅在用户明确愿意测试时执行。

真人 E2E 默认不需要重复测试 send/forward，因为 v0.1.9 已对 Saved Messages 做过真实 write E2E；v0.3 若要复验 write 仍须先 dry-run + 用户确认。

# Known Bugs

截至本快照，**没有已知未修复的 v0.3 Candidate blocker**。最新自动化 gate 全绿；真正未知项集中在真实 Telegram 账号 E2E。

历史关键 bug/事故（已修，保留为回归知识）：

- qasync blocking modal → asyncio task re-entry；
- packaged Windows cp1252 中文 JSON → error handler `UnicodeEncodeError` → exit 1；
- migrated global advanced-search legacy cursor → 重复/遗漏；
- migrated rich-get logical/source chat ID 不一致。

# Known Risks

- GitHub branches 当前未启用 branch protection；PR/no-force-push 纪律靠 Agent 自觉；
- v0.3 尚未真实账号系统 E2E；mock/CI 不能覆盖 Telegram 实际 participant、Forum、migration、Saved Messages 差异；
- Telegram API 对历史管理员任期、匿名管理员真实身份、已删除消息均有限制；代码必须保持“unknown/unavailable”而不是猜；
- media download 是本地磁盘副作用，真实文件尺寸/网络中断仍需谨慎；
- 旧 v0.1.x binary 与 v0.3 daemon 同时运行会故意触发 SessionLease compatibility boundary；
- PR #17/#19 仍 open Draft，未来 Agent 可能误认为是待实施工作，必须以 #20 为准。

# Technical Debt

- `docs/DECISIONS.md` 历史上是单文件累积；本 handoff 开始为关键长期决策建立 ADR，旧 D-xxx 保留为索引/历史；
- v0.2 没有单独正式 Release，第三代直接继承；代际说明必须一直保留，避免版本号误读；
- v0.3 full design docs 当前随 PR #20 分支存在，直到 #20 正式合并前，默认 main 只能通过 HANDOFF/ADR/PR 链接恢复完整背景；
- MCP 仍只是 future direction；不要提前把 v0.3 扩成 MCP/后台监听 Agent。

# Important Constraints

- 历史 AppData 路径不能迁移：`%APPDATA%\TelegramMultiChatExporter\`；
- 不删除用户历史 JSON、分类删除不删磁盘内容；
- 不复制/绕过 Telegram Session lock；
- 不从同名推断 migration；
- 不从显示名/`post_author` 推断匿名管理员；
- 不把 missing message 说成“已删除”；
- 不把 reader 变成隐式 mark-read/write；
- 不把 Actions artifact 当正式 Release；
- 杀软误报/代码签名当前明确降优先级，不要自行把它拉回主线。

# Production Safety Boundaries

- 不读取、输出、提交或修改用户真实 Secret/Session 内容；
- 不提交 `api_id/api_hash`、phone、OTP、2FA、access_hash、file_reference、IPC auth secret；
- 不删除/迁移 `%APPDATA%\TelegramMultiChatExporter\`；
- 不通过删 lock、复制 `.session` 来解决并发；
- 不直接 push/force-push main；
- 不删除/覆盖历史 tags/Releases；
- 未经明确授权，不真实 send/forward/mark-read；真人 write 测试只优先 Saved Messages；
- 未经用户明确确认，不执行真实 media download；
- 不开放 daemon TCP/HTTP/Web endpoint；
- 不向 GitHub Actions 放真实 Telegram credentials。

完整安全模型见 `docs/SECURITY_MODEL.md` 与 `SECURITY.md`。

# Recent Decisions

关键长期决定已/将以 ADR 持久化：

- single local daemon 唯一持有 Telegram Session；
- Windows Named Pipe + authenticated UTF-8 JSON bytes，不用 TCP/HTTP/pickle；
- reader bounded pagination + HMAC/query-bound safe cursor；
- Telegram write safety：dry-run/caps/ambiguity/FloodWait/unknown-outcome-no-retry；
- Basic Group→Supergroup 使用一个 logical chat，legacy 仅作历史 source；
- v0.3 human E2E 是 merge/release 硬闸门；MCP 不属于当前版本。

# Next Steps

1. 用户下载 frozen Candidate artifact `9726786295`；
2. 按 `docs/TESTING.md` 的 v0.3 human E2E checklist 只读优先测试；
3. 若发现问题：只修实际问题 → regression test → Windows CI → 受影响真人场景复验；
4. 若全部 PASS：更新 PR #20/Candidate Notes/HANDOFF 的 E2E 结果；
5. 用户明确说“发布 v0.3.0”之后，才把 Candidate Notes 收尾成 Release Notes并进入 merge/release；
6. 正式 release workflow 成功后核验 tag/target/assets/SHA256，并更新 HANDOFF 为新的 Production 状态。

# Recommended Next Task

**不要开发新功能。** 下一项工作是陪用户执行 v0.3 frozen Candidate 的真实 Telegram 账号 E2E，并把每项 PASS/FAIL 结果写回 PR #20/HANDOFF。只有测试暴露缺陷才改代码。

# How To Resume

新 Agent 接手当前工作时：

1. 查看 `main` 当前 HEAD 和 Latest Release，确认 Production 是否仍为 v0.1.10；
2. 查看 PR #20 是否仍 OPEN/DRAFT、base 是否仍 `main`、head 是否仍与本快照一致；
3. 查看 `codex/personal-account-reader-v0.3.0` 最新 commit；
4. 查看 PR #20 最新 Windows CI；
5. 读 PR #20 分支的 `HANDOFF.md`、`docs/PERSONAL_ACCOUNT_READER_V3_DESIGN.md`、`docs/DAEMON_IPC_DESIGN.md`；
6. 若用户尚未真人 E2E，不写新功能；直接进入 E2E checklist；
7. 如果 GitHub 状态比本文件更新，以 GitHub 为准，并先修正 HANDOFF 再继续。

# New Chat Resume Instructions

新的 GPT 接手本项目时，必须先完成：

1. 阅读 `AGENTS.md`；
2. 阅读 `HANDOFF.md`；
3. 阅读 `README.md`；
4. 阅读 `docs/ARCHITECTURE.md`；
5. 阅读 `docs/SECURITY_MODEL.md` 和 `SECURITY.md`；
6. 阅读 `docs/TESTING.md`、`docs/DEPLOYMENT.md`、`docs/RELEASE_PROCESS.md`；
7. 阅读与当前任务相关的 `docs/decisions/` ADR；
8. 查看 open PR #20、PR #17、PR #19，并明确 #17/#19 是历史设计、#20 是当前实施；
9. 查看 `main`、`codex/personal-account-reader-v0.3.0` 与最新 commits；
10. 查看 Latest Release/Tags 与当前 CI。

完成以上步骤之前**不要修改代码**。

然后先向用户输出四项：

- 当前项目状态；
- 当前任务；
- 当前风险/安全边界；
- 推荐下一步。

确认恢复无误后再继续开发或真人验收。