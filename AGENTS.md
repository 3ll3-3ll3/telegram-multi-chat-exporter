# AGENTS.md

本文件是任何后续 Agent / Codex / 自动化开发者进入本仓库后的**第一阅读入口**。除非用户明确改变产品方向，否则以下规则视为项目长期不变量。

## 1. 开工前必须阅读

按顺序阅读：

1. `AGENTS.md`（本文件）
2. `HANDOFF.md`（当前状态、最近变更、未发布修复、下一步）
3. `docs/ARCHITECTURE.md`
4. `docs/DECISIONS.md`
5. `docs/TESTING.md`
6. 涉及发布时再读 `docs/RELEASE_PROCESS.md`
7. 涉及 JSON 兼容时再读 `docs/JSON_COMPATIBILITY.md`

不要仅凭 README 推断当前实现状态；README 面向用户，`HANDOFF.md` 才是开发交接快照。

## 2. 产品核心定位（不可擅自改变）

这是 **Windows GUI Telegram 多群独立批次文本导出器**，不是 Telegram 客户端替代品，也不是累计归档数据库。

必须保持：

- 每次运行生成一个独立批次目录。
- 每个群生成自己的 `result.json`。
- 历史批次**不合并、不回写、不建设 master DB**。
- 每个群可独立使用三种规则：
  - 指定时间范围；
  - 当前未读；
  - 上次成功导出以后。
- 只导出文字；**不下载照片、视频、文件、语音、贴纸等媒体**。
- 媒体消息如果有 caption，可保留 caption 文字。
- JSON 是权威数据格式；未来若加 HTML，只能作为由 JSON 本地生成的阅读视图，不能成为第二份独立抓取结果。
- GUI 优先，最终用户不应被要求使用命令行。

## 3. 群组工作区不变量

账号可能有数百/上千个群。完整列表只作为“群组目录”。

- 主编辑面板只展示用户在“选择群组”中勾选的工作群。
- 已选群 ID 保存在本地 `settings.json`。
- 不要退回“登录后把所有群直接铺满主表格”的旧行为。

## 4. 未读与已读策略（高风险区域）

“当前未读”必须使用刷新群组目录时冻结的快照：

```text
read_inbox_max_id < message_id <= latest_message_id_at_refresh
```

因此导出过程中后来到达的消息：

- 不进入本批次；
- 不能被本批次“导出后标已读”误标。

项目采用 **Option B**：每群独立 `导出后标已读` 开关。

规则：

- 默认 OFF。
- 仅 `当前未读` 模式可启用。
- 配置按群持久化在本地。
- 严格顺序：

```text
result.json 成功写入
→ 更新本地导出 checkpoint
→ 可选 Telegram read acknowledgement
```

- 导出失败：绝不能改变 Telegram 已读状态。
- 标已读失败：JSON 仍然算成功，单独报告 read-ack 失败。
- Telegram 已读是按 message ID 推进的，因此开启后，快照范围内未写入 JSON 的媒体/服务消息也可能一起变成已读；UI 必须明确提示。
- 除用户显式启用该开关外，普通导出/刷新/查看目录不得发送已读确认。

## 5. qasync / Telethon GUI 规则（不要破坏）

Telethon 后台任务与 Qt 共用 qasync 事件循环。历史上已经出现过 nested Qt event loop 导致：

```text
RuntimeError: Cannot enter into task ... while another task ... is being executed
```

因此：

- Telethon 连接后不要在 async slot 中使用会启动嵌套事件循环的 `QDialog.exec()`、静态 `QMessageBox.*()`、静态 `QInputDialog.getText()` 等。
- 使用现有非阻塞 dialog + await `finished` 的模式。
- 当前窗口继承链和职责见 `docs/ARCHITECTURE.md`；若要重构，必须先补回归测试，不能简单删掉 qasync-safe 层。
- 退出流程必须容忍 Telethon `disconnect()` 在不同事件循环状态下返回 awaitable 或直接完成。
- shutdown 清理异常不应升级成 PyInstaller 的致命 “Unhandled exception in script” 弹窗。

## 6. Telegram 网络与代理

- Windows 上会检测已启用的系统代理并显式传给 Telethon。
- Clash/Mihomo 常见 `127.0.0.1:7890` 场景应在不强制开启 TUN 的情况下可工作。
- 不要假设 Telegram Desktop 自己的内部代理会自动被 Telethon 继承。
- 代理日志只记录安全标签/端点，不记录任何 Telegram Secret。

## 7. 本地数据与安全边界

运行时目录：

```text
%APPDATA%\TelegramMultiChatExporter\
```

其中可能包含：

- `api_credentials.json`
- `telegram.session`
- `local_state.json`
- `settings.json`
- `logs\app.log`

严格禁止提交或打印：

- `api_hash`
- 手机号
- 登录验证码
- 2FA 密码
- `.session` 内容
- 用户聊天正文（日志也不要记录）

`local_state.json` 只能保存 checkpoint 等必要状态，不保存消息正文。

## 8. Telegram Desktop JSON 兼容目标

当前目标是：**纯文本范围内尽量兼容 Telegram Desktop JSON 的结构与常用字段**，不是完整克隆 Telegram Desktop 全量导出器。

不要为了“兼容”而开始下载媒体。

已知兼容缺口必须在 `docs/JSON_COMPATIBILITY.md` 保持更新，包括：

- rich text entities；
- chat type；
- top-level chat id；
- service/forward metadata；
- whitespace 原样性；
- media metadata（多数为产品刻意不支持）。

## 9. 开发与 Git 规则

默认流程：

1. 从最新 `main` 新建功能/修复分支。
2. 小步提交。
3. 跑测试和 Windows CI。
4. PR 说明行为变化、风险和测试。
5. CI 全绿后合并。
6. 有用户可见二进制变化时，按 `docs/RELEASE_PROCESS.md` 发新版本。

不要：

- 强推覆盖 `main`；
- 为了解冲突丢掉 main 上已经存在的修复；
- 在未验证 Windows 打包前宣称 Release 可用；
- 把 Actions Artifact 当长期正式下载入口（正式分发使用 GitHub Releases）。

文档-only 改动一般不需要版本号和 Release。

## 10. 最低测试门槛

任何功能变更至少要通过：

```text
pytest -q
GUI import check
Windows PyInstaller build
packaged EXE --smoke-test
```

Release 还必须验证：

- one-file EXE；
- portable onedir；
- 两者 smoke-test；
- SHA256SUMS 生成；
- Release assets 上传成功。

涉及真实 Telegram 行为时，CI 不能替代真人账号 E2E；在 `HANDOFF.md` 标明仍需用户验证的部分。

## 11. 交接纪律

每次完成以下任一事项后，都要更新 `HANDOFF.md`：

- 用户可见功能；
- 关键 bug 修复；
- 架构变化；
- 新 Release；
- 新的已知问题；
- 用户已完成的真实账号验证。

如果改变长期设计决策，同时更新 `docs/DECISIONS.md`。

一个合格的交接应让下一个 Agent 在不依赖聊天上下文的情况下回答：

- 目前正式最新版是什么？
- main 是否有未发布提交？
- 哪些功能已经用户实测？
- 哪些只是 CI 通过？
- 当前最高优先级 bug/兼容缺口是什么？
- 下一次发布应该做什么？
