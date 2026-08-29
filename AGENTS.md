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

这是 **Windows GUI Telegram 多群独立文本导出器**，不是 Telegram 客户端替代品，也不是累计归档数据库。

必须保持：

- 每次对某群的导出都是**独立 JSON 文件**；历史 JSON 不读取、不合并、不回写。
- v0.1.8 起不再使用“整次运行一个批次目录 + 每群 result.json”的输出布局；正式布局为：

```text
总输出目录 / 导出分类 / 群组 / YYYY-MM-DD_HH-mm-ss.json
```

- 同一群同一秒重复导出必须避免覆盖，使用 `_2`、`_3` 等后缀。
- 导出分类是 **TG Exporter 自己的本地分类**，由软件 UI 创建和管理；不是 Telegram Chat Folder。
- 每个群可独立保存自己的导出分类；分类对应总输出目录下一级文件夹，不存在时自动创建。
- 软件里删除分类不得删除磁盘历史 JSON/目录；只影响未来可选分类。
- 不建设 master DB，不做跨历史 JSON 的累计合并。
- 每个群可独立使用三种规则：
  - 指定时间范围；
  - 当前未读；
  - 上次成功导出以后。
- **聊天消息导出**只保留文字；不下载消息中的照片、视频、文件、语音、贴纸等媒体。
- 媒体消息如果有 caption，可保留 caption 文字。
- 唯一媒体例外：群/频道**资料头像**可以仅为群组选择器 UI 按需下载小图并缓存在本机；头像不得写入 JSON 或导出目录，也不得扩展成聊天媒体备份。
- JSON 是权威数据格式；未来若加 HTML，只能作为由 JSON 本地生成的阅读视图，不能成为第二份独立抓取结果。
- GUI 优先，最终用户不应被要求使用命令行。

## 3. 群组工作区、Telegram 分组与导出分类

账号可能有数百/上千个群。完整列表只作为“群组目录”。

- 主编辑面板只展示用户在“选择群组”中勾选的工作群。
- 已选群 ID 保存在本地 `settings.json`。
- 不要退回“登录后把所有群直接铺满主表格”的旧行为。
- 优先复用 Telegram 账号已有 Chat Folders / Dialog Filters 做**群组选择筛选**。
- Telegram Chat Folder 只读，不创建/修改/删除账号分组。
- **导出分类**是另一套完全本地的概念：用于决定文件落盘目录，由 `管理分类` 创建。
- 每群分类分配保存在 `settings.json` 的 `group_export_categories`；自定义分类列表保存在 `export_categories`。
- 保留内置 `未分类` 作为安全默认值。
- v0.1.7 起选择器头像采用按需加载：默认首字占位，只加载当前屏幕附近可见项，受限并发，本地缓存；头像失败必须静默降级，不得阻断选择器。

## 4. 普通群升级超级群（迁移）

Telegram 会在 Basic Group 升级为 Supergroup 后保留一个 migrated legacy Chat。官方客户端通常隐藏旧 Chat。

从 v0.1.8 起：

- 群组目录不得把迁移前旧 Basic Group 和当前 Supergroup 同时显示为两条。
- 必须以**当前超级群**作为主实体；修复重复项不得删除、退出或修改真实超级群。
- 旧 Basic Group peer id 作为 `GroupInfo.migrated_from_chat_id` 保留，仅用于历史兼容。
- 若旧 peer 曾保存在 `selected_group_ids`、`mark_read_after_export`、`group_export_categories`，应迁移到当前超级群 ID；不要把旧消息 checkpoint 直接复制成新超级群 checkpoint，因为两套消息 ID 语义不能假定一致。
- `当前未读` 和 `上次导出以后` 只针对当前超级群。
- `指定时间范围` 在存在 `migrated_from_chat_id` 时，应读取旧 Basic Group + 当前 Supergroup，并按时间合并到同一个本次 JSON。
- 如果旧历史读取失败，不要伪装成完整成功；正确性优先。

## 5. 未读与已读策略（高风险区域）

“当前未读”必须使用刷新群组目录时冻结的快照：

```text
read_inbox_max_id < message_id <= latest_message_id_at_refresh
```

因此导出过程中后来到达的消息：

- 不进入本次；
- 不能被本次“导出后标已读”误标。

项目采用 **Option B**：每群独立 `导出后标已读` 开关。

规则：

- 默认 OFF。
- 仅 `当前未读` 模式可启用。
- 配置按群持久化在本地。
- 严格顺序：

```text
本次 JSON 成功原子写入
→ 更新本地导出 checkpoint
→ 可选 Telegram read acknowledgement
```

- 导出失败：绝不能改变 Telegram 已读状态。
- 标已读失败：JSON 仍然算成功，单独报告 read-ack 失败。
- Telegram 已读是按 message ID 推进的，因此开启后，快照范围内未写入 JSON 的媒体/服务消息也可能一起变成已读；UI 必须明确提示。
- 除用户显式启用该开关外，普通导出/刷新/查看目录不得发送已读确认。

## 6. qasync / Telethon GUI 规则（不要破坏）

Telethon 后台任务与 Qt 共用 qasync 事件循环。历史上已经出现过 nested Qt event loop 导致：

```text
RuntimeError: Cannot enter into task ... while another task ... is being executed
```

因此：

- Telethon 连接后不要在 async slot 中使用会启动嵌套事件循环的 `QDialog.exec()`、静态 `QMessageBox.*()`、静态 `QInputDialog.getText()` 等。
- 使用现有非阻塞 dialog + await `finished` 的模式。
- `管理分类` 等新对话框也必须走现有 `_await_dialog()`；对话框内部普通按钮事件可以同步处理，但不得引入第二 Qt/asyncio loop。
- 当前窗口继承链和职责见 `docs/ARCHITECTURE.md`；若要重构，必须先补回归测试，不能简单删掉 qasync-safe 层。
- 头像异步加载也必须运行在同一个 qasync/asyncio loop；关闭选择器时取消未完成头像任务，不建立第二事件循环。
- 退出流程必须容忍 Telethon `disconnect()` 在不同事件循环状态下返回 awaitable 或直接完成。
- shutdown 清理异常不应升级成 PyInstaller 的致命 “Unhandled exception in script” 弹窗。

## 7. Telegram 网络与代理

- Windows 上会检测已启用的系统代理并显式传给 Telethon。
- Clash/Mihomo 常见 `127.0.0.1:7890` 场景应在不强制开启 TUN 的情况下可工作。
- 不要假设 Telegram Desktop 自己的内部代理会自动被 Telethon 继承。
- 代理日志只记录安全标签/端点，不记录任何 Telegram Secret。

## 8. 本地数据与安全边界

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
- `cache\avatars\`（群组选择器 UI 小头像缓存）

`settings.json` 还会保存：工作群选择、每群标已读偏好、导出分类列表、每群分类分配和总输出目录。

严格禁止提交或打印：

- `api_hash`
- 手机号
- 登录验证码
- 2FA 密码
- `.session` 内容
- 用户聊天正文（日志也不要记录）
- 本地头像缓存二进制

`local_state.json` 只能保存 checkpoint 等必要状态，不保存消息正文。

## 9. Telegram Desktop JSON 兼容目标

当前目标是：**纯文本范围内尽量兼容 Telegram Desktop JSON 的结构与常用字段**，不是完整克隆 Telegram Desktop 全量导出器。

不要为了“兼容”而开始下载聊天消息媒体。选择器头像只是本地 UI 装饰，不属于 JSON 兼容范围。

已知兼容缺口必须在 `docs/JSON_COMPATIBILITY.md` 保持更新，包括：

- rich text entities；
- chat type；
- top-level chat id；
- service/forward metadata；
- whitespace 原样性；
- media metadata（多数为产品刻意不支持）。

迁移群跨旧/新 peer 合并时，当前仍保留各自原消息 ID；不要在没有官方依据时擅自重编号。

## 10. 开发与 Git 规则

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

## 11. 最低测试门槛

任何功能变更至少要通过：

```text
pytest -q
GUI import check
Windows PyInstaller build
packaged EXE --smoke-test
```

输出分类/迁移相关变更至少还应覆盖：

- 分类名 Windows 安全校验；
- 分类文件夹自动创建；
- 同秒导出不覆盖；
- `分类 / 群组 / 日期时间.json` 路径；
- migrated legacy Chat 不重复出现在 catalogue；
- DATE_RANGE 会读取 legacy + current 两个 peer；
- 旧工作区/分类/标已读 UI 偏好迁移到当前超级群。

Release 还必须验证：

- one-file EXE；
- portable onedir；
- 两者 smoke-test；
- SHA256SUMS 生成；
- Release assets 上传成功。

涉及真实 Telegram 行为时，CI 不能替代真人账号 E2E；在 `HANDOFF.md` 标明仍需用户验证的部分。头像、Telegram Folder 和 migrated supergroup 尤其需要真实账号验证。

## 12. 交接纪律

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
