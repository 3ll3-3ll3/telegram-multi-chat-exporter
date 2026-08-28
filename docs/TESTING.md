# Testing Guide

本项目有两类验证：

1. **CI 可自动验证**：模型、serializer、proxy、GUI import、PyInstaller 打包、smoke-test。
2. **必须真实 Telegram 账号验证**：登录、read marker、真实群导出、Desktop differential test。

不要把 CI green 等同于“真实 Telegram E2E 已验证”。

## 1. 本地/CI 基线

开发环境：

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
pytest -q
```

最低回归门槛：

```text
pytest -q
GUI import check
Windows one-file build
packaged EXE --smoke-test
```

正式 Release 还要验证 portable onedir。

## 2. Smoke-test 的边界

`launcher.py --smoke-test` 只验证打包产物能导入 GUI/module 并正常退出 smoke path。

它**不验证**：

- Telegram 网络；
- API credentials；
- phone/code/2FA；
- read acknowledgement；
- 真实聊天历史；
- Desktop JSON 一致性。

## 3. 首次登录 E2E

在 Windows 正式/候选 EXE：

1. 使用本人的 `api_id` / `api_hash`。
2. 若依赖 Clash/Mihomo，保持 Windows system proxy 开启。
3. 登录手机号使用国际格式。
4. 完成 code / 2FA。
5. 查看日志确认：

```text
Detected Windows system proxy: ...
Telegram transport connected
authorized=True/False as expected
```

安全要求：不要把 api_hash、手机号、code、2FA 写进 issue/PR/log sample。

## 4. Focused workspace E2E

真实账号可能有大量群：

1. 登录并加载完整 catalogue。
2. 确认主表不会直接显示全部群。
3. 点击 `选择群组`。
4. 搜索并选择 5–10 个工作群。
5. 重启程序，确认选择持久化。
6. 再打开 selector，确认未选择的群仍留在 catalogue 但不在主工作表。

## 5. Mixed-mode five-group test

至少选 5 个群：

- 2 个 date range；
- 1 个 current unread（read ack OFF）；
- 1 个 current unread（read ack ON，最好用低风险测试群）；
- 1 个 since-last。

预期：

- 一次运行只生成一个 batch directory；
- 每群单独子目录与 `result.json`；
- 某群失败不应中止其他群；
- 不下载任何媒体文件；
- caption 可作为文字出现。

## 6. Date-range boundary test

验证本地日期 inclusive：

- 当天 00:00 附近消息；
- 当天 23:59 附近消息；
- 起始日前一条；
- 结束日后一条。

确保用户选择的日期边界与输出一致。

## 7. Current-unread frozen snapshot test

刷新 catalogue 时记录：

```text
lower = read_inbox_max_id
upper = latest_message_id
```

然后在导出期间让群里新增消息。

预期：

- 输出只包含 `lower < id <= upper`；
- 新消息 id > upper 不进入当前 JSON。

如果 `unread_count == 0`：

- 生成合法空 JSON；
- 不遍历整个历史。

## 8. Read-policy Option B E2E

### OFF

1. 手机端保留 N 条未读。
2. 工具 current-unread 导出，`导出后标已读` OFF。
3. 导出成功后检查手机/Desktop。

预期：未读状态不变。

### ON

选低风险测试群：

1. 刷新 catalogue，记录 upper message id。
2. 开启 `导出后标已读`。
3. 导出过程中再产生一条 id > upper 的新消息。
4. 等导出成功。

预期：

- JSON 只到 upper；
- read marker 只推进到 upper；
- later arrival 保持未读；
- 如果 read ack 失败，JSON 仍保留且 GUI 单独报告。

注意：upper 范围内纯媒体/服务消息即使不在文本 JSON，也可能随 Telegram read marker 一起变已读，这是设计已知副作用。

## 9. Since-last checkpoint test

首次没有 checkpoint：

- 必须提示先做 date-range/current-unread；
- 不得默默从群历史第一条开始。

成功导出后：

- checkpoint 单调不减。
- 后来导出更老的历史 date range 不得让 checkpoint 后退。

## 10. Shutdown regression test

针对历史 bug：

```text
TypeError: object NoneType can't be used in 'await' expression
```

测试：

1. 登录成功并加载群。
2. 正常关闭窗口。
3. 重复“连接后立即关闭 / 导出后关闭 / 已断网后关闭”。

预期：

- 不弹 PyInstaller `Unhandled exception in script`；
- shutdown 问题最多写日志；
- Session 不被无故删除。

## 11. Telegram Desktop differential test

选一个小群和固定窗口：

1. Telegram Desktop 导出 machine-readable JSON。
2. 本工具用同一时间范围导出。
3. 按 message id 对齐比较。

重点：

```text
message count
id
date/date_unixtime
from/from_id
reply_to_message_id
edited
text
text_entities
chat type
chat id
```

差异分类写入 `JSON_COMPATIBILITY.md` 和 `HANDOFF.md`。

## 12. Output integrity

每次批次检查：

- JSON 是有效 UTF-8；
- 文件可完整 `json.load()`；
- 每群结果互不覆盖；
- 两个清洗后同名群不能碰撞（当前为待修复项，修复后补测试）；
- result atomic write 修复后，应模拟中断并确认不留下半文件。

## 13. Security checks

公开仓库/CI logs 不得出现：

- api_hash；
- phone；
- verification code；
- 2FA password；
- `.session`；
- 聊天正文。

运行时状态只在用户本地 AppData 与用户选择的 export 目录。
