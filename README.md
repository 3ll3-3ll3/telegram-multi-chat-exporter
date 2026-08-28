# Telegram Multi-Chat Exporter

一个面向 Windows 的 Telegram 多群批次文本消息导出工具。

## 核心目标

- GUI 优先，不要求用户熟悉命令行。
- 一次勾选多个群组，每个群组拥有**独立的导出规则**。
- 每个群可分别选择：
  - 指定时间范围；
  - 当前未读消息；
  - 自该群上次成功导出以后。
- 只导出文字，不下载图片、视频、语音或文件；带媒体的消息可保留文字 caption。
- 每个群生成独立 `result.json`。
- 每次运行生成独立批次目录，不与历史批次合并，不建设消息总库。
- JSON 字段尽量兼容 Telegram Desktop 的导出风格。
- Telegram 登录凭据和 `.session` 仅存放在本机用户目录，绝不写入仓库。

## 日常使用

1. 首次打开 EXE，输入 Telegram `api_id` / `api_hash` 并登录。
2. GUI 自动列出账号可访问的群组。
3. 主表格中每个群独立设置导出方式和日期范围。
4. 点击“开始导出”。
5. 在选定输出目录获得一个独立批次文件夹，每个群一个 `result.json`。

## Telegram 连接与诊断

`v0.1.1` 起加入 GUI 诊断功能：

- **API 设置**：第一次填错 `api_id` / `api_hash` 后可以直接修改，不必手工删除配置文件。
- **重置登录**：清除本程序的本地 Telegram Session，解决 Session 失效/冲突后重新登录的问题。
- **打开日志目录**：直接打开本地日志文件夹。
- 常见 Telegram API / 验证码 / 2FA / Flood Wait / 网络错误会转换成中文提示。

日志默认位置：

```text
%APPDATA%\TelegramMultiChatExporter\logs\app.log
```

日志采用 5 MB 轮转，最多保留 5 个历史文件。程序不会主动记录 `api_hash`、手机号、验证码、2FA 密码或 Session 内容，Telethon 也不会开启 wire-level DEBUG 日志。

### 首次连接失败时

1. 确认 Telegram 官方桌面端在当前电脑和网络下能正常连接。
2. 点击 **API 设置**，确认使用的是 `my.telegram.org` → **API development tools** 里的 `api_id` 和 `api_hash`，不是 BotFather 的 Bot Token。
3. 手机号使用国际格式，例如 `+86xxxxxxxxxxx`。
4. 如果提示 Session 无效或冲突，点击 **重置登录** 后重新连接。
5. 仍失败时点击 **打开日志目录**，查看 `app.log` 中最后一次错误。

## 开发运行

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
python -m telegram_exporter
```

## 安全

公开仓库中禁止提交：

- Telegram `api_hash`
- 手机号、验证码、2FA 密码
- `*.session`
- 本地日志
- 本地导出结果

这些内容均由应用在本机运行时创建。
