# Security Policy

本项目处理 Telegram 登录状态和聊天导出，因此默认采用“本地最小权限、最少持久化”原则。

## Sensitive data that must stay local

以下内容不得提交到 GitHub、Issue、PR、CI log 或公开文档：

- Telegram `api_hash`
- 手机号
- 登录验证码
- 2FA 密码
- `*.session` / session journal
- 用户聊天正文
- 用户真实导出文件

## Local runtime files

默认位于：

```text
%APPDATA%\TelegramMultiChatExporter\
```

可能包含：

```text
api_credentials.json
telegram.session
local_state.json
settings.json
logs\app.log
```

这些文件不是发布资产。

## Logging rules

日志允许记录：

- 阶段名称；
- 安全的 error type/message；
- proxy host/port；
- api_id（不是 api_hash）；
- 群标题和 message count（如现有实现需要）。

日志禁止记录：

- api_hash；
- phone/code/2FA；
- Session 内容；
- message body。

新增 debug 日志时，先判断对象的 `repr()` 是否可能泄露敏感字段。

## Telegram write operations

默认导出是只读行为。

唯一当前允许的 Telegram 状态写入是用户对某群显式开启 `导出后标已读` 后的 read acknowledgement。

必须满足：

```text
result.json success → checkpoint success → optional read ack
```

导出失败不得改变 read marker。

不要增加自动发消息、删除消息、退群、改群设置等写操作，除非用户明确新增产品需求且 UI 明示该副作用。

## Build and release

GitHub Actions 不需要 Telegram Secret。正式发布产物来自仓库源码构建。

正式用户下载入口：

```text
https://github.com/3ll3-3ll3/telegram-multi-chat-exporter/releases/latest
```

Release 应包含 SHA256SUMS。

## Vulnerability / accidental secret response

如果发现 Secret 被误提交：

1. 不要只做普通删除后认为问题结束；Git 历史可能仍包含数据。
2. 立即停止传播该值。
3. 撤销/轮换对应凭据或 Session。
4. 清理 Git 历史或使用 GitHub 的敏感数据处理流程。
5. 在 `HANDOFF.md` 记录安全事件的非敏感摘要和后续要求。

## Antivirus/signing

当前杀软误报/代码签名不是项目活跃开发主线。不要通过关闭杀软、自动加白名单、规避检测等方式“解决”误报。
