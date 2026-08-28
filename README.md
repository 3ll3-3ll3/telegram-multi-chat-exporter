# TG Exporter

**TG 导出器**：一个面向 Windows 的 Telegram 多群批次文本消息导出工具。

> 从 v0.1.6 起，产品展示名由 “Telegram Multi-Chat Exporter” 缩短为 **TG Exporter / TG 导出器**。为避免升级后丢失登录状态和配置，历史本地数据目录 `%APPDATA%\TelegramMultiChatExporter\` 继续沿用。

## 核心目标

- GUI 优先，不要求用户熟悉命令行。
- Telegram 账号里的全部群组只作为**群组目录**加载；主编辑面板只显示你主动选择的固定工作群。
- “选择群组”可直接读取 Telegram 账号已有的**聊天文件夹 / 分组**，先按分组缩小目录，再搜索和勾选目标群。
- 一次可处理多个工作群，每个群拥有**独立的导出规则**。
- 每个群可分别选择：指定时间范围、当前未读消息、自该群上次成功导出以后。
- 只导出文字，不下载图片、视频、语音或文件；带媒体的消息可保留文字 caption。
- 每个群生成独立 `result.json`。
- 每次运行生成独立批次目录，不与历史批次合并，不建设消息总库。
- JSON 字段尽量兼容 Telegram Desktop 的导出风格。
- Telegram 登录凭据和 `.session` 仅存放在本机用户目录，绝不写入仓库。

## 日常使用

1. 首次打开 EXE，输入 Telegram `api_id` / `api_hash` 并登录。
2. 程序加载账号可访问的完整群组/频道目录，但不会把它们全部铺到主界面。
3. 点击 **选择群组**。可以先在 **Telegram 分组** 下拉框中选择账号已有聊天文件夹，再在当前分组里搜索并勾选真正需要处理的工作群；选择会保存在本机，下次继续使用。
4. 主表格中仅对这些工作群分别设置导出方式和日期范围。
5. 点击 **开始导出**。
6. 在选定输出目录获得一个独立批次文件夹，每个群一个 `result.json`。

Telegram 分组只用于读取和筛选：本工具不会创建、修改或删除你账号里的聊天文件夹。如果某个 Telegram 文件夹只包含私聊/机器人而没有群组或频道，它不会出现在本工具的群组选择器里。

## 三种导出模式

### 指定时间范围

完全按该群自己的开始/结束日期导出，适合周期性批次。不同群可以选择不同时间范围。

### 当前未读

以点击连接/刷新群组目录时 Telegram 返回的已读边界和最新消息位置为一个**冻结快照**。本次只处理该快照中的未读消息；导出过程中后来到达的新消息不会混入本批次。

默认行为是**只读导出**：读取并导出未读消息不会自动改变 Telegram 的已读状态。

每个群额外有一个独立的 **导出后标已读** 开关：

- 默认关闭；
- 只在“当前未读”模式下可用；
- 开关选择按群保存在本机；
- 只有该群的 `result.json` 成功写入后，程序才会发送 Telegram 已读确认；
- 如果导出失败，绝不会改变该群已读状态；
- 如果 JSON 已成功但 Telegram 已读确认失败，JSON 会保留，并单独提示“标已读失败”；
- 已读确认只推进到本次刷新时冻结的最新消息 ID，不会把刷新之后到达的新消息标成已读。

注意：Telegram 的已读状态按消息 ID 推进，而本工具只导出文本。因此如果开启“导出后标已读”，该快照范围内的图片、文件、系统消息等未被写入 JSON 的非文本项，也可能一起变成已读。

### 上次导出以后

使用本工具为该群保存的最后成功导出消息位置作为起点。它与 Telegram 的“未读”是两套不同概念：即使你在手机上读过消息，“上次导出以后”仍可继续导出本工具尚未处理的新内容。

## Telegram 连接、代理与诊断

- **API 设置**：第一次填错 `api_id` / `api_hash` 后可以直接修改。
- **重置登录**：清除本程序的本地 Telegram Session 后重新登录。
- **打开日志目录**：直接打开本地日志文件夹。
- 常见 Telegram API / 验证码 / 2FA / Flood Wait / 网络错误会转换成中文提示。
- `v0.1.2` 起，在 Windows 上如果“系统代理”已启用，本程序会自动读取该代理端点并显式交给 Telethon。典型 Clash/Mihomo 的 `127.0.0.1:7890` 可以在不启用 TUN 的情况下使用。
- `v0.1.3` 起，登录和主要消息框使用 qasync 安全的非嵌套对话框流程，避免 Telethon 后台任务与 Qt 嵌套事件循环重入。
- `v0.1.5` 起，“选择群组”可读取 Telegram 账号同步的 Chat Folders / Dialog Filters，并在选择器内按账号分组筛选。
- `v0.1.6` 起，产品展示名和发布文件名统一缩短为 **TG Exporter / TGExporter.exe**。

日志默认位置：

```text
%APPDATA%\TelegramMultiChatExporter\logs\app.log
```

日志采用 5 MB 轮转，最多保留 5 个历史文件。程序不会主动记录 `api_hash`、手机号、验证码、2FA 密码、Session 内容或聊天正文。

### 首次连接失败时

1. 确认 Telegram 官方桌面端在当前电脑和网络下能正常连接。
2. 点击 **API 设置**，确认使用的是 `my.telegram.org` → **API development tools** 里的 `api_id` 和 `api_hash`，不是 BotFather 的 Bot Token。
3. 如果本机依赖 Clash/Mihomo，确保 Windows“系统代理”处于启用状态；日志会显示程序检测到的代理类型、主机和端口。
4. 手机号使用国际格式，例如 `+86xxxxxxxxxxx`。
5. 如果提示 Session 无效或冲突，点击 **重置登录** 后重新连接。
6. 仍失败时点击 **打开日志目录**，查看 `app.log` 中最后一次错误。

## Release 下载

正式版本发布到 GitHub Releases。发布流程提供：

- 单文件 EXE：`TGExporter-vX.Y.Z-windows-x64.exe`；
- portable ZIP：`TGExporter-vX.Y.Z-windows-x64-portable.zip`；
- `SHA256SUMS.txt`：发布文件完整性校验。

固定最新版入口：

```text
https://github.com/3ll3-3ll3/telegram-multi-chat-exporter/releases/latest
```

## 开发者 / Agent 接手

本仓库会由不同 Agent 持续交接开发。**不要只读 README 就开始修改。**

固定阅读顺序：

1. [`AGENTS.md`](AGENTS.md) — 长期产品不变量、开发禁区、测试门槛。
2. [`HANDOFF.md`](HANDOFF.md) — 当前正式版本、main 未发布修复、用户实测状态、下一步。
3. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — 当前实际启动链、GUI/qasync/Telethon 架构。
4. [`docs/DECISIONS.md`](docs/DECISIONS.md) — 已接受的设计决策。
5. [`docs/TESTING.md`](docs/TESTING.md) — CI + 真人 Telegram E2E 测试矩阵。
6. [`docs/RELEASE_PROCESS.md`](docs/RELEASE_PROCESS.md) — Windows Release 流程。
7. [`docs/JSON_COMPATIBILITY.md`](docs/JSON_COMPATIBILITY.md) — 与 Telegram Desktop JSON 的兼容边界。
8. [`SECURITY.md`](SECURITY.md) — Secret、Session、日志和 Telegram 写操作安全规则。

重大功能、关键 bug、Release 或用户真实 E2E 结果完成后，必须同步更新 `HANDOFF.md`；长期设计方向变化同时更新 `docs/DECISIONS.md`。

## 开发运行

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python -m telegram_exporter
```

安装后也可使用短命令：

```powershell
tg-exporter
```

旧命令 `telegram-multi-chat-exporter` 暂时保留兼容。

## License

MIT License，见 [`LICENSE`](LICENSE)。

## 安全

公开仓库中禁止提交：Telegram `api_hash`、手机号、验证码、2FA 密码、`*.session`、本地日志和本地导出结果。这些内容均由应用在本机运行时创建。完整规则见 [`SECURITY.md`](SECURITY.md)。
