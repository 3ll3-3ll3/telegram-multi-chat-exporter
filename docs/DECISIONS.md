# Design Decisions

本文件记录已经明确采用、后续 Agent 不应随意反转的设计决策。若用户明确改变方向，应修改对应条目并在 `HANDOFF.md` 记录。

## D-001：独立导出文件，不做累计归档

**状态：Accepted（v0.1.8 更新）**

用户明确将旧的“每次运行创建批次目录，每群一个 `result.json`”改为长期分类目录结构：

```text
总输出目录 / 导出分类 / 群组 / YYYY-MM-DD_HH-mm-ss.json
```

每次对某群导出仍然是**独立 JSON 文件**。历史 JSON 不被读取、合并或重写；同秒冲突自动追加 `_2`、`_3`，绝不覆盖旧文件。

理由：用户希望同一个群长期归在固定分类/群组目录下，按导出日期直接积累独立 JSON，而不是按整次运行批次查找。

## D-002：JSON 是权威数据源

**状态：Accepted**

JSON 是主格式。未来如增加 HTML，只允许从已生成的 JSON 本地渲染为阅读视图，不能重新抓 Telegram 形成第二套数据源。

理由：JSON 更适合后续程序处理、AI/RAG、筛选、去重和与 Telegram Desktop 导出兼容。

## D-003：消息导出文本优先，不下载聊天媒体

**状态：Accepted**

消息导出阶段不下载照片、视频、音频、语音、贴纸和文件。媒体消息存在文字 caption 时可以保留 caption。

群/频道的**资料头像**不属于聊天消息导出内容；从 v0.1.7 起允许仅为群组选择器按需下载小头像并缓存在本机 UI cache。头像不得进入 JSON，也不得因此扩展成聊天媒体备份功能。

理由：产品目标仍是文本批量处理，不是完整备份工具；头像只是帮助用户在大量群组中快速识别目标。

## D-004：每群规则完全独立

**状态：Accepted**

同一次开始导出中，不同群可以分别使用 date range、current unread、since last export，并拥有各自导出分类，不使用全局单一时间规则或单一分类。

## D-005：Focused workspace

**状态：Accepted**

完整 Telegram dialog 列表只作为 catalogue。主导出表格只显示用户在“选择群组”中选中的工作群，选择跨启动持久化。

理由：真实账号可能有数百/上千个群，实际只处理固定少量群。

## D-006：未读使用冻结快照

**状态：Accepted**

刷新 catalogue 时冻结：

```text
lower = read_inbox_max_id
upper = latest_message_id
```

本次 current-unread 只处理：

```text
lower < id <= upper
```

导出过程中后来到达的消息留到下一次。

## D-007：Option B 已读策略

**状态：Accepted**

每群有独立 `导出后标已读` 开关：默认关闭，仅 current-unread 模式可用。

严格顺序：

```text
本次 JSON write success
→ local checkpoint update
→ optional read acknowledgement(max_id=snapshot upper bound)
```

失败导出不得改变已读状态；read-ack 失败不得删除已成功生成的 JSON。

## D-008：qasync 单事件循环 + 非阻塞 Dialog

**状态：Accepted**

Qt GUI 与 Telethon 使用 qasync 共享 asyncio event loop。Telethon 活跃时不得使用会启动 nested Qt event loop 的阻塞 modal API。

历史事故：`QDialog.exec()` / static dialog 在 async slot 中触发 qasync task re-entry RuntimeError。

当前做法：`dialog.open()` + await `finished`。

## D-009：Windows 系统代理显式传给 Telethon

**状态：Accepted**

Telethon 原生 TCP 不假设自动继承 Windows system proxy。程序检测 Windows 已启用的 system proxy，并显式创建 Telethon proxy 配置。

目标场景：Clash/Mihomo `127.0.0.1:7890`，无需为本工具强制开 TUN。

## D-010：Telegram Desktop 兼容是“文本范围内尽量一致”

**状态：Accepted**

不追求 Telegram Desktop 全量导出器 1:1 克隆。优先匹配普通文本的核心字段和语义；媒体元数据不作为必须能力。

兼容缺口见 `JSON_COMPATIBILITY.md`。

## D-011：正式二进制只通过 GitHub Releases 分发

**状态：Accepted**

Actions Artifact 是 CI 临时产物；用户长期下载入口是 Releases。Release 同时保留 one-file EXE、portable ZIP、SHA256SUMS。

## D-012：本地状态最小化

**状态：Accepted**

`local_state.json` 只保存每群必要 checkpoint，不保存聊天正文。凭据、Session、settings、logs 全部只在本机 AppData。

导出分类列表和每群分类分配属于 UI 配置，保存在 `settings.json`，不进入 `local_state.json`。

## D-013：杀软误报/代码签名暂不作为当前开发主线

**状态：Accepted (user-deprioritized)**

用户已明确要求不继续处理 360 相关问题。除非后续重新提出，不要主动消耗开发周期在 360 申诉、SignPath 等工作上。

## D-014：优先复用 Telegram 账号自带聊天分组

**状态：Accepted**

“选择群组”不能只依靠在数百/上千个群中搜索名称。程序应读取 Telegram 账号已经同步的 Chat Folders / Dialog Filters，并允许用户先按账号现有分组缩小群组目录，再搜索、勾选工作群。

规则：

- 这些分组是**选择器视图**，不是本工具另建的一套云端分类；
- 不修改、创建或删除用户 Telegram 里的分组；只读取；
- 需要尊重 Telegram folder 的显式 include/exclude 和 group/broadcast、exclude_read、exclude_muted、exclude_archived 等动态规则；
- 文件夹读取失败不得阻止原来的完整 catalogue + 搜索功能；
- 主编辑面板仍然只显示最终勾选的 focused workspace，不因为增加文件夹功能而重新铺满全部群。

## D-015：产品展示名缩短为 TG Exporter

**状态：Accepted**

从 v0.1.6 起，用户可见品牌统一为：

```text
TG Exporter
TG 导出器
TGExporter.exe
```

内部 Python 包名 `telegram_exporter` 不因品牌变化而重构；这样可以避免无意义的大范围 import 迁移。

为保证已有用户升级后继续复用 Telegram Session、API 设置、工作群选择和日志，历史本地数据目录：

```text
%APPDATA%\TelegramMultiChatExporter\
```

继续作为兼容路径使用，不随品牌名迁移。

## D-016：群组选择器头像采用按需加载

**状态：Accepted**

为了让大量群组更容易识别，选择器显示 Telegram 群/频道资料头像，并采用以下边界：

- 默认先显示确定性的圆形首字占位；
- 只请求当前屏幕附近可见条目的小头像，不在打开选择器时批量抓取全部群头像；
- 并发请求受限，避免数百群账号产生突发请求；
- 成功头像仅缓存在本机 AppData，默认缓存约 7 天；
- 头像加载失败不得影响选择器、Telegram 登录或消息导出；
- 头像不写入 JSON，不复制到导出目录；
- 此能力不得被解释为允许下载聊天消息里的图片/视频/文件。

选择器视觉基线：约 42 px 圆形头像、约 58 px 行高、双行文字（群名 + `@username`/类型/未读辅助信息）。

## D-017：导出分类由软件自己管理

**状态：Accepted**

从 v0.1.8 起，“导出分类”是 TG Exporter 的本地概念，与 Telegram Chat Folder 严格区分。

规则：

- 用户在软件内点击 `管理分类` 新建分类；
- 分类名必须可安全作为 Windows 文件夹名，不能静默把非法字符改写成另一个名字；
- 自定义分类列表保存在 `settings.json` 的 `export_categories`；
- 每群分类分配保存在 `group_export_categories`；
- 内置 `未分类` 永远作为默认兜底；
- 当前总输出目录下缺少分类目录时自动创建；
- 删除分类只移除未来 UI 选项，不自动删除磁盘上的历史目录/JSON；
- 更换总输出目录后，分类目录应在新根目录按需重新创建。

## D-018：Basic Group → Supergroup 只显示一个逻辑群

**状态：Accepted**

Telegram 底层升级群组时会保留 migrated legacy Basic Group，并创建/使用当前 Supergroup。用户明确要求不因为底层迁移导致选择器出现同名重复群。

采用：

- 当前 Supergroup 是唯一主实体；
- legacy Basic Group 不作为独立 catalogue 行显示；
- legacy peer id 保存到 `GroupInfo.migrated_from_chat_id`；
- 修复只改变本工具视图，不删除、退出、修改 Telegram 超级群；
- 已选群、标已读偏好、导出分类等 UI 设置可从旧 peer id 迁到新 peer id；
- `local_state.json` 旧 checkpoint 不直接复制到新 peer，因为旧/新消息 ID 序列不能假设等价；
- current-unread / since-last 只读当前 Supergroup；
- date-range 同时读取 legacy + current，并按时间合并成一个独立 JSON；
- 当前不擅自对旧/新 peer 中可能重复的 message id 做重编号。
