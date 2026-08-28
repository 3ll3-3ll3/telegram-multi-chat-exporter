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

## 计划中的日常体验

1. 首次打开 EXE，输入 Telegram `api_id` / `api_hash` 并登录。
2. GUI 自动列出账号可访问的群组，勾选需要管理的群。
3. 主表格中每个群独立设置导出方式和日期范围。
4. 点击“开始导出”。
5. 在选定输出目录获得一个独立批次文件夹，每个群一个 `result.json`。

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
- 本地导出结果

这些内容均由应用在本机运行时创建。
