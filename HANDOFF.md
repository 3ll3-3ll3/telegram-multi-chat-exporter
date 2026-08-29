# HANDOFF.md

> 这是本仓库的**当前开发交接快照**。任何 Agent 接手前先读 `AGENTS.md`，再读本文件。完成用户可见功能、关键修复或 Release 后必须更新本文件。

更新时间：2026-08-29

## 1. 当前版本状态

### 最新正式 Release

- 当前已发布：**TG Exporter v0.1.7**
- 仓库：`https://github.com/3ll3-3ll3/tg-exporter`
- Release: `https://github.com/3ll3-3ll3/tg-exporter/releases/tag/v0.1.7`
- Release target commit: `63034d2e15677e2579af5763a89b8a9fe81143ff`
- Release workflow run: `33227209870`，全部成功。
- 正式单文件：`TGExporter-v0.1.7-windows-x64.exe`
- EXE SHA-256：`22a67e7551cb60e983734106aa9cc92b2f48dce85c8142372f11668252f03629`
- Portable：`TGExporter-v0.1.7-windows-x64-portable.zip`
- Portable SHA-256：`0fb39d291de486972a98701791a3dd21e5005d18cec80c61004077fc702c48b3`

### v0.1.8 candidate

当前功能分支：`feat/export-categories-migration-v0.1.8`

PR：`https://github.com/3ll3-3ll3/tg-exporter/pull/15`

用户在 2026-08-29 明确改变旧输出结构，要求：

```text
总输出目录/
├─ 第一类/
│  ├─ 群组1/
│  │  ├─ YYYY-MM-DD_HH-mm-ss.json
│  │  └─ ...
│  └─ 群组2/
│     └─ ...
└─ 第二类/
   ├─ 群组3/
   ├─ 群组4/
   └─ 群组5/
```

分类必须在软件内直接创建；目录不存在自动生成。旧的“每次运行 batch directory / 群/result.json”不再是产品目标。

v0.1.8 candidate 已实现：

- `管理分类` 非阻塞 GUI；
- 自定义分类保存在 `settings.json -> export_categories`；
- 每群分类分配保存在 `group_export_categories`；
- 内置 `未分类` 默认分类；
- 分类名做 Windows-safe 校验，不静默改写非法分类名；
- 新分类立即在当前总输出目录下创建对应文件夹；
- 更换输出根目录后分类目录自动建立；
- 软件内删除分类**不删除磁盘历史数据**；
- 每群导出路径改为 `output/category/group/timestamp.json`；
- 同秒文件冲突使用 `_2/_3/...`，不覆盖；
- 聊天 JSON 改为 `.tmp -> replace` 原子写入，同时保留 indent=1；
- 主表新增“分类”列；
- 旧的“选中群设为最近10天”批量按钮已适配新增列。

用户同时反馈某些群在选择器出现两遍，并询问是否与超级群有关。检查确认当前 Telethon catalogue 会返回 migrated legacy Basic Group。用户确认只要不会影响真实超级群，就按建议修复。

v0.1.8 candidate 已实现：

- 读取 dialog 时识别 legacy Basic Group 的 `migrated_to`；
- legacy row 不再作为独立 catalogue 项显示；
- 当前 Supergroup 仍是唯一主实体，不删除、不退群、不修改 Telegram 账号状态；
- `GroupInfo.migrated_from_chat_id` 保存旧 peer id；
- 旧 `selected_group_ids`、`mark_read_after_export`、`group_export_categories` UI 偏好迁到当前 Supergroup；
- **不复制旧 local checkpoint 到新 peer**；
- current-unread / since-last 只操作当前 Supergroup；
- DATE_RANGE 会读取 legacy Basic Group + current Supergroup，并按 `(date, id)` 排序后生成一个 JSON；
- legacy history 读取失败时该群导出应失败，不静默冒充完整结果。

`VERSION=v0.1.8`，`pyproject.toml=0.1.8`。

## 2. 用户已实际验证过什么

已由真实账号验证：

- Telegram API 登录成功。
- Windows 系统代理检测可识别 Clash `http://127.0.0.1:7890`。
- Telethon transport 通过该代理成功连接 Telegram。
- 账号 Session 可保存并复用。
- 用户实际观察到：部分群在当前 v0.1.7 选择器中出现两遍；这构成 v0.1.8 migrated-group 修复的真实触发场景。

曾由用户日志定位并修复：

1. 系统代理未被 Telethon 自动继承 → v0.1.2 起显式读取 Windows 系统代理。
2. qasync nested modal dialog 重入 → v0.1.3 改为非阻塞 dialog await 模式。
3. 关闭程序时 `await None` → v0.1.5 起已包含修复。

尚待用户真实账号 E2E：

- Telegram 分组下拉框是否与账号实际 Chat Folders 名称/成员一致；
- v0.1.7+ 群头像是否正确显示，滚动/筛选是否不卡顿；
- v0.1.8 `管理分类` 创建/持久化/删除语义；
- v0.1.8 `分类/群组/时间戳.json` 是否符合用户实际工作习惯；
- 用户看到的重复群是否在 v0.1.8 中确实只剩当前 Supergroup 一条；
- 跨升级日期 DATE_RANGE 是否能同时拿到迁移前后真实历史；
- `导出后标已读` 对手机/桌面端 read marker 的真实同步；
- 与 Telegram Desktop 同一群/同一时间窗口的 JSON differential test。

## 3. 当前/候选用户可见能力

正式 v0.1.7：

- Windows PySide6 GUI，`TG Exporter / TG 导出器`；
- Telegram 登录与 Session 复用；
- Windows system proxy -> Telethon；
- searchable focused workspace；
- Telegram Chat Folder 筛选；
- 42 px 圆形头像 + 58 px 双行选择器记录；
- 三种每群独立导出模式；
- frozen unread；
- Option B 每群 `导出后标已读`；
- text/caption-only JSON；
- one-file + portable Releases。

v0.1.8 候选新增：

- 本地导出分类管理；
- 每群分类持久化；
- `分类/群组/日期时间.json`；
- atomic chat JSON write；
- migrated Basic Group -> current Supergroup catalogue collapse；
- date-range migration history stitching。

## 4. 三种“分组/分类”概念不要混淆

### Telegram Chat Folder

账号同步的 Dialog Filters，只用于群组选择器筛选，**只读**。

### Focused workspace

用户最终勾选、放在主表里的工作群集合，`selected_group_ids` 持久化。

### Export Category

TG Exporter 自己的本地导出分类，用于落盘路径：

```text
output_root/category/group/timestamp.json
```

不要把 Export Category 写回 Telegram Chat Folder。

## 5. Telegram migration 实现说明

当前 catalogue path：

```text
client.iter_dialogs()
→ collect eligible group/channel dialogs
→ entity.migrated_to ?
   ├─ yes: record legacy peer -> target supergroup, skip legacy row
   └─ no: build GroupInfo
→ attach migrated_from_chat_id to matching current GroupInfo
→ apply Telegram Dialog Filters
→ selector
```

不要仅按“同名”去重；必须依赖 Telegram 显式 migration relation，否则会误合并两个真实同名群。

DATE_RANGE path：

```text
legacy peer (if migrated)
+ current peer
→ independent Telethon iter_messages calls
→ collect text/caption
→ sort by date/id
→ one JSON
```

current-unread/since-last 不访问 legacy peer。

## 6. 关键产品不变量

除非用户再次明确改变：

- 不建设累计 master DB；历史 JSON 不合并、不回写。
- 输出结构使用 `总输出目录 / 导出分类 / 群组 / 日期时间.json`。
- 分类由软件本地管理；删除分类不删除历史文件。
- 聊天消息不下载照片/视频/语音/文件/贴纸；JSON 是权威数据源。
- 群/频道资料头像仅是选择器 UI 例外。
- 每群规则与分类独立；主工作区只显示用户选中的少量群。
- Telegram Chat Folders 仅用于选择器筛选，不修改账号分组。
- migrated legacy Basic Group 不重复显示；当前 Supergroup 永远是主实体。
- 默认导出不改变 Telegram 已读状态；read ack 必须由用户按群明确开启，且 JSON 成功后才能发送。
- GUI-first。
- 产品展示名 `TG Exporter / TG 导出器`；AppData 兼容路径继续 `%APPDATA%\TelegramMultiChatExporter\`。

## 7. 当前代码结构

启动链：

```text
launcher.py
→ telegram_exporter.main
→ telegram_exporter.focused_gui.MainWindow
```

GUI：

```text
gui.py
→ gui_async.py
→ focused_gui.py
```

新增/关键模块：

- `category_manager.py`：软件内分类 dialog；
- `export_categories.py`：分类校验/目录/时间戳/同秒冲突；
- `group_selector.py`：Telegram Folder + 搜索 + avatar；
- `telegram_service.py`：catalogue + migration collapse + avatar；
- `exporter.py`：模式查询 + migrated date-range + categorized atomic JSON；
- `read_state.py`：Option B；
- `storage.py`：settings/state atomic JSON。

## 8. 当前可靠性 / JSON 技术债

已在 v0.1.8 candidate 顺手解决：聊天 JSON atomic write。

仍需：

- sanitized duplicate group-title folder collision；
- Telegram Desktop chat type / top-level id；
- whitespace 原样保留；
- rich text entities；
- forward/service metadata；
- migrated legacy/current message id 重叠时与 Desktop 的精确语义；
- GUI 三层收敛；
- 每行实时进度/失败重试。

## 9. 未读与已读语义

刷新 catalogue：

```text
read_inbox_max_id < id <= latest_message_id
```

`导出后标已读`：

```text
atomic JSON success
→ local checkpoint
→ send_read_acknowledge(max_id=latest_message_id)
```

Telegram read marker 按 ID 推进，因此快照内未进入 JSON 的媒体/系统消息也可能一起变已读；UI 必须持续提示。

migrated legacy history 不参与 current unread read ack。

## 10. 本地文件与安全

兼容目录：

```text
%APPDATA%\TelegramMultiChatExporter\
```

典型内容：

```text
api_credentials.json
telegram.session
local_state.json
settings.json
logs\app.log
cache\avatars\*
```

`settings.json` 新增/使用：

```text
output_dir
selected_group_ids
mark_read_after_export
export_categories
group_export_categories
```

仓库和日志禁止出现 api_hash、手机号、验证码、2FA、Session 内容、聊天正文、真实头像 cache。

## 11. 发布要求

- `VERSION` 与 `pyproject.toml` 必须一致。
- PR #15 的 Windows CI 必须全绿后才可合并。
- 合并时使用 `release: v0.1.8`，触发正式 Release workflow。
- 正式 Release 必须通过：pytest、GUI import、one-file、portable、两种 packaged smoke-test、SHA256SUMS、Release upload。
- Release 后把本文件从 candidate 改为正式状态，并记录 target commit / hashes / workflow run。

## 12. v0.1.8 真人验收重点

1. `管理分类` 在软件里创建“第一类/第二类”；
2. 输出根目录自动出现分类文件夹；
3. 群1/2 -> 第一类，群3/4/5 -> 第二类，重启后仍保存；
4. 导出后路径准确为 `分类/群/时间戳.json`；
5. 同一天/同秒重复导出不覆盖；
6. 删除软件分类不删除历史文件；
7. 原先出现两遍的迁移群现在只显示当前 Supergroup 一条；
8. 当前 Supergroup 不消失、不退群、不受修改；
9. 跨迁移日期范围能包含旧+新历史；
10. 旧 Session/settings 继续复用。

## 13. 当前不做

除非用户重新提出：360/杀软误报与签名、完整聊天媒体备份、云端消息数据库、自动绕过安全软件。
