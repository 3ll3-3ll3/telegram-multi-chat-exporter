# Design Decisions

本文件记录已经明确采用、后续 Agent 不应随意反转的设计决策。若用户明确改变方向，应修改对应条目并在 `HANDOFF.md` 记录。

## D-001：独立批次，不做累计归档

**状态：Accepted**

每次运行创建新的批次目录，每群一个 `result.json`。历史批次不被读取、合并或重写。

理由：用户的工作方式是每隔若干天独立导出固定若干群，而不是维护长期 master database。

## D-002：JSON 是权威数据源

**状态：Accepted**

JSON 是主格式。未来如增加 HTML，只允许从已生成的 JSON 本地渲染为阅读视图，不能重新抓 Telegram 形成第二套数据源。

理由：JSON 更适合后续程序处理、AI/RAG、筛选、去重和与 Telegram Desktop 导出兼容。

## D-003：文本优先，不下载媒体

**状态：Accepted**

不下载照片、视频、音频、语音、贴纸和文件。媒体消息存在文字 caption 时可以保留 caption。

理由：产品目标是文本批量处理，不是完整备份工具。

## D-004：每群规则完全独立

**状态：Accepted**

同一批次内不同群可以分别使用 date range、current unread、since last export，不使用全局单一时间规则。

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

导出过程中后来到达的消息留到下一批。

## D-007：Option B 已读策略

**状态：Accepted**

每群有独立 `导出后标已读` 开关：默认关闭，仅 current-unread 模式可用。

严格顺序：

```text
result.json write success
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
