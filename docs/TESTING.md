# Testing Guide

本项目有两类验证：

1. **CI 可自动验证**：模型、serializer、分类路径、迁移 collapse、proxy、GUI import、PyInstaller 打包、smoke-test。
2. **必须真实 Telegram 账号验证**：登录、Chat Folder、群头像、read marker、真实 migrated supergroup、真实群导出、Desktop differential test。

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
- Telegram Chat Folder 真实成员；
- 真实群头像；
- read acknowledgement；
- migrated legacy history；
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

## 4. Focused workspace + Telegram Folder E2E

真实账号可能有大量群：

1. 登录并加载完整 catalogue。
2. 确认主表不会直接显示全部群。
3. 点击 `选择群组`。
4. 确认 Telegram 分组下拉框与账号 Chat Folders 基本一致。
5. 在某个 Chat Folder 内搜索并选择 5–10 个工作群。
6. 确认头像可见项按需加载，无头像群保持首字占位。
7. 重启程序，确认选择持久化。
8. 再打开 selector，确认未选择的群仍留在 catalogue 但不在主工作表。

## 5. Export Category E2E

### 创建与目录

1. 选择一个测试输出根目录，例如 `D:\TG导出测试`。
2. 点击 `管理分类`。
3. 新建 `第一类`、`第二类`。
4. 保存。

预期：

```text
D:\TG导出测试\第一类\
D:\TG导出测试\第二类\
D:\TG导出测试\未分类\
```

均存在。

### 每群分配

选择 5 个工作群：

```text
群1 -> 第一类
群2 -> 第一类
群3 -> 第二类
群4 -> 第二类
群5 -> 第二类
```

关闭/重开软件后，确认每群分类分配仍保存。

### 删除分类

在软件里删除一个已有分类。

预期：

- 它不再作为未来分类选项；
- 原磁盘分类文件夹和历史 JSON **不删除**；
- 原来指向已删除分类的群回退到 `未分类`。

## 6. Mixed-mode five-group test

至少选 5 个群：

- 2 个 date range；
- 1 个 current unread（read ack OFF）；
- 1 个 current unread（read ack ON，最好用低风险测试群）；
- 1 个 since-last；
- 分布到至少 2 个导出分类。

预期：

```text
总输出根目录/
├─ 第一类/
│  ├─ 群1/YYYY-MM-DD_HH-mm-ss.json
│  └─ 群2/YYYY-MM-DD_HH-mm-ss.json
└─ 第二类/
   ├─ 群3/YYYY-MM-DD_HH-mm-ss.json
   ├─ 群4/YYYY-MM-DD_HH-mm-ss.json
   └─ 群5/YYYY-MM-DD_HH-mm-ss.json
```

并且：

- 同一次开始导出使用同一个时间戳 stem；
- 不再创建旧的整次 batch directory；
- 某群失败不应中止其他群；
- 不下载任何聊天媒体文件；
- caption 可作为文字出现；
- JSON 可 `json.load()`。

## 7. Same-second no-overwrite test

对同一个群/分类构造同一导出时间 stem，两次落盘。

预期：

```text
2026-08-29_18-55-01.json
2026-08-29_18-55-01_2.json
```

不覆盖第一份。第三次应为 `_3`。

## 8. Date-range boundary test

验证本地日期 inclusive：

- 当天 00:00 附近消息；
- 当天 23:59 附近消息；
- 起始日前一条；
- 结束日后一条。

确保用户选择的日期边界与输出一致。

## 9. Migrated Basic Group -> Supergroup E2E

优先选一个确实曾从普通群升级为超级群的真实群。

### Catalogue

1. 在 Telegram Desktop/手机确认只有一个当前超级群。
2. TG Exporter 刷新 catalogue。
3. 搜索该群。

预期：

- 只显示一个当前 Supergroup；
- 不再出现迁移前 Basic Group 的同名重复行；
- 当前超级群本身不会消失、退群或被修改。

### UI preference migration

如果旧版曾选择过 legacy row/分配过分类或标已读偏好，升级后检查这些 UI 设置尽量落到当前 Supergroup。

不要期望旧 `local_state.json` checkpoint 自动复制到新 peer。

### Long date range

选择一个跨越“升级为超级群”时间点的 date range。

预期：

- 迁移前旧群文本能出现；
- 迁移后当前超级群文本能出现；
- 最终只生成一个本次 JSON；
- 内容按时间排序；
- 如果 legacy peer 读取失败，程序应明确报该群导出失败，而不是静默声称完整成功。

### Current unread / since-last

这两种模式只操作当前 Supergroup，不查询 legacy Basic Group。

## 10. Current-unread frozen snapshot test

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

## 11. Read-policy Option B E2E

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
- 文件先成功原子写入分类目录；
- checkpoint 更新后才发 read ack；
- read marker 只推进到 upper；
- later arrival 保持未读；
- 如果 read ack 失败，JSON 仍保留且 GUI 单独报告。

注意：upper 范围内纯媒体/服务消息即使不在文本 JSON，也可能随 Telegram read marker 一起变已读，这是设计已知副作用。

## 12. Since-last checkpoint test

首次没有 checkpoint：

- 必须提示先做 date-range/current-unread；
- 不得默默从群历史第一条开始。

成功导出后：

- checkpoint 单调不减。
- 后来导出更老的历史 date range 不得让 checkpoint 后退。
- migrated legacy history 的 message id 不得被直接当成当前 Supergroup checkpoint。

## 13. Shutdown regression test

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

## 14. Telegram Desktop differential test

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

对 migrated group 另记录：legacy/current 两套 message id 是否会发生重叠，以及 Telegram Desktop 对这类历史的实际输出语义。不要未经验证自行重编号。

差异分类写入 `JSON_COMPATIBILITY.md` 和 `HANDOFF.md`。

## 15. Output integrity

每个导出文件检查：

- JSON 是有效 UTF-8；
- 文件可完整 `json.load()`；
- atomic `.tmp -> replace` 不留下半写 JSON；
- 每群每次结果互不覆盖；
- 分类名不能包含 Windows 非法路径字符/保留设备名；
- 两个清洗后同名群目录 collision 当前仍为待修复项。

## 16. Security checks

公开仓库/CI logs 不得出现：

- api_hash；
- phone；
- verification code；
- 2FA password；
- `.session`；
- 聊天正文。

运行时状态只在用户本地 AppData 与用户选择的 export 目录。

`管理分类` 的删除操作不得递归删除用户历史导出目录。
