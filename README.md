# Telegram Multi-Chat Exporter

一个面向 Windows 的 Telegram 多群批次文本消息导出工具。

## 核心目标

- GUI 优先，不要求用户熟悉命令行。
- 账号中的全部群组只作为**群组目录**加载；主编辑面板只显示用户主动选择的少量工作群。
- 一次勾选多个工作群，每个群组拥有**独立的导出规则**。
- 每个群可分别选择：指定时间范围、当前未读消息、自该群上次成功导出以后。
- 只导出文字，不下载图片、视频、语音或文件；带媒体的消息可保留文字 caption。
- 每个群生成独立 `result.json`。
- 每次运行生成独立批次目录，不与历史批次合并，不建设消息总库。
- JSON 字段尽量兼容 Telegram Desktop 的导出风格。
- Telegram 登录凭据和 `.session` 仅存放在本机用户目录，绝不写入仓库。

## 日常使用

1. 首次打开 EXE，输入 Telegram `api_id` / `api_hash` 并登录。
2. 程序后台加载账号可访问的群组/频道目录，但不会把全部群组铺满主界面。
3. 点击 **选择群组**，在可搜索列表中勾选常用的 5～10 个工作群；选择会保存到本机。
4. 主表格只显示已选工作群，每个群独立设置导出方式和日期范围。
5. 点击“开始导出”。
6. 在选定输出目录获得一个独立批次文件夹，每个群一个 `result.json`。

## 当前未读模式的语义

`当前未读` 是**只读导出**：程序读取 Telegram 当前的已读边界，然后抓取该边界之后的消息，但不会主动调用 Telegram 的 `readHistory` / `send_read_acknowledge` 一类接口。

因此：

- 使用本工具导出未读消息，**不会因为导出动作本身让手机或 Telegram Desktop 上的消息变成已读**；
- 如果你之后在手机、Desktop 或其他 Telegram 客户端真正读了这些消息，它们会正常变成已读；
- 下一次再次使用“当前未读”时，范围以 Telegram 服务器那时的真实未读状态为准；
- `v0.1.3` 起会在刷新群组目录时同时记录每个群当时的最新消息 ID，从而把“当前未读”冻结为一个快照，避免导出过程中刚到达的新消息混入本批次。

当前版本**没有**“导出成功后自动标记 Telegram 已读”的行为。若后续增加该功能，应作为显式可选项，并且默认关闭。

## Telegram 连接、代理与诊断

- **API 设置**：第一次填错 `api_id` / `api_hash` 后可以直接修改。
- **重置登录**：清除本程序的本地 Telegram Session 后重新登录。
- **打开日志目录**：直接打开本地日志文件夹。
- 常见 Telegram API / 验证码 / 2FA / Flood Wait / 网络错误会转换成中文提示。
- `v0.1.2` 起，在 Windows 上如果“系统代理”已启用，本程序会自动读取该代理端点并显式交给 Telethon。典型 Clash/Mihomo 的 `127.0.0.1:7890` 可以在不启用 TUN 的情况下使用。
- `v0.1.3` 起，首次登录验证码对话框改为非嵌套事件循环方式，避免 qasync 与 Telethon 后台任务发生重入冲突。

日志默认位置：

```text
%APPDATA%\TelegramMultiChatExporter\logs\app.log
```

日志采用 5 MB 轮转，最多保留 5 个历史文件。程序不会主动记录 `api_hash`、手机号、验证码、2FA 密码、Session 内容或聊天正文。

### 首次连接失败时

1. 确认 Telegram 官方桌面端在当前电脑和网络下能正常连接。
2. 点击 **API 设置**，确认使用的是 `my.telegram.org` → **API development tools** 里的 `api_id` 和 `api_hash`，不是 BotFather 的 Bot Token。
3. 如果本机依赖 Clash/Mihomo，确保 Windows “系统代理”处于启用状态；日志会显示程序检测到的代理类型、主机和端口。
4. 手机号使用国际格式，例如 `+86xxxxxxxxxxx`。
5. 如果提示 Session 无效或冲突，点击 **重置登录** 后重新连接。
6. 仍失败时点击 **打开日志目录**，查看 `app.log` 中最后一次错误。

## Release 下载

正式版本发布到 GitHub Releases，并提供：

- 单文件 EXE：最方便；
- portable ZIP：PyInstaller onedir 构建，不使用 one-file 自解压层；
- `SHA256SUMS.txt`：发布文件完整性校验。

## 开发运行

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python -m telegram_exporter
```

## License

MIT License，见 [`LICENSE`](LICENSE)。

## 安全

公开仓库中禁止提交：Telegram `api_hash`、手机号、验证码、2FA 密码、`*.session`、本地日志和本地导出结果。这些内容均由应用在本机运行时创建。
