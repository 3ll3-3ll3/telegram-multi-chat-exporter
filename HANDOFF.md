# HANDOFF.md

> 这是本仓库的**当前开发交接快照**。任何 Agent 接手前先读 `AGENTS.md`，再读本文件。完成用户可见功能、关键修复或 Release 后必须更新本文件。

更新时间：2026-08-29

## 1. 当前版本状态

### 最新正式 Release

- 当前已发布：**TG Exporter v0.1.8**
- 仓库：`https://github.com/3ll3-3ll3/tg-exporter`
- Release：`https://github.com/3ll3-3ll3/tg-exporter/releases/tag/v0.1.8`
- Release target commit：`8bd83eb2869f3843b353d727b612688d0ecfcd91`
- 功能 PR：#15 `https://github.com/3ll3-3ll3/tg-exporter/pull/15`
- PR 最新 Windows CI run：`33249861481`，pytest / GUI import / one-file build / packaged smoke-test / artifact 全部成功。
- 正式 Release workflow run：`33249950869`，pytest / GUI import / one-file / portable / 两种 packaged smoke-test / SHA256 / Release upload 全部成功。
- 正式单文件：`TGExporter-v0.1.8-windows-x64.exe`
- EXE SHA-256：`3de70bd1c70df94370e0639a81146f033db955bce638b5f5a3504c3cc4581439`
- Portable：`TGExporter-v0.1.8-windows-x64-portable.zip`
- Portable SHA-256：`9650f5e6c2c510c08821bd38ea0ff1898157321076f88708d6814c158c14057f`
- `SHA256SUMS.txt` asset digest：`abe059adee4c772adb3577e78e6cbc0912f9431a555f8fd00fa852275ddcba94`

`main` 在 Release target 后仅允许有文档/交接类提交时不必另发二进制；若有功能代码变更必须重新评估版本。

## 2. v0.1.8 已发布功能

用户在 2026-08-29 明确改变旧输出结构。正式产品输出现在是：

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

不再以“整次运行 batch directory / 群/result.json”作为当前产品布局。

已发布实现：

- 软件内 `管理分类` 非阻塞 GUI；
- 自定义分类保存在 `settings.json -> export_categories`；
- 每群分类分配保存在 `group_export_categories`；
- 内置 `未分类` 默认分类；
- 分类名做 Windows-safe 校验，不静默改写非法分类名；
- 新分类在当前总输出目录下自动创建对应一级文件夹；
- 更换输出根目录后分类目录自动建立；
- 软件内删除分类**不删除磁盘历史目录/JSON**，只移除未来选项；
- 每群输出为 `output/category/group/timestamp.json`；
- 同秒文件冲突用 `_2/_3/...`，绝不覆盖；
- 聊天 JSON 使用 `.tmp -> replace` 原子写入，仍保持 UTF-8 / `ensure_ascii=False` / `indent=1`；
- 主表新增“分类”列；
- 旧“选中群设为最近10天”按钮已适配新列。

## 3. Basic Group -> Supergroup 重复项修复

用户真实账号在 v0.1.7 观察到：部分群在选择器出现两遍。检查后确认 Telethon catalogue 可能同时返回迁移前 legacy Basic Group 和当前 Supergroup。

v0.1.8 已发布：

- 根据 Telegram 显式 `entity.migrated_to` 关系识别迁移，不按同名猜测去重；
- legacy Basic Group 不再作为独立 catalogue 行显示；
- 当前 **Supergroup 永远是主实体**；
- 该修复不会删除、退出、修改、降级真实 Telegram 超级群，也不会写入群设置；
- `GroupInfo.migrated_from_chat_id` 保存 legacy peer id，只用于历史兼容；
- 旧 `selected_group_ids`、`mark_read_after_export`、`group_export_categories` UI 偏好尽量迁到当前 Supergroup；
- **不复制旧 local checkpoint 到新 peer**，因为两套消息 ID 不能假定等价；
- `当前未读` / `上次导出以后` 只操作当前 Supergroup；
- `指定时间范围` 在检测到迁移关系时读取 legacy Basic Group + current Supergroup，按 `(date, id)` 排序后生成一个本次 JSON；
- legacy history 读取失败时该群导出失败，不静默冒充完整成功；
- 当前保留旧/新 peer 原始 message id，不擅自重编号。

## 4. 用户已实际验证过什么

真实账号已经验证：

- Telegram API 登录成功；
- Windows system proxy 可识别 Clash `http://127.0.0.1:7890`；
- Telethon transport 可通过该代理连接；
- Session 可保存并复用；
- v0.1.7 真实观察到部分群重复，这是 v0.1.8 migration collapse 的触发场景。

曾由用户日志定位并修复：

1. 系统代理未被 Telethon 自动继承 → v0.1.2；
2. qasync nested modal dialog 重入 → v0.1.3；
3. 关闭程序 `await None` → v0.1.5 正式包含。

**仍待真实账号 E2E（CI 不能替代）：**

- Telegram Chat Folder 名称/成员与账号实际是否完全一致；
- 群头像真实对应、滚动/筛选性能；
- v0.1.8 `管理分类` 创建/持久化/删除体验；
- `分类/群组/时间戳.json` 是否符合实际长期使用；
- 用户原先重复的 migrated 群在 v0.1.8 是否确实只剩当前 Supergroup 一条；
- 跨升级日期的 DATE_RANGE 是否能拿到迁移前后完整真实历史；
- `导出后标已读` 对手机/Desktop read marker 的真实同步；
- 与 Telegram Desktop 同群同窗口 JSON differential test。

## 5. 三种“分组/分类”概念不要混淆

### Telegram Chat Folder

账号同步 Dialog Filters，只用于**选择群**，只读，不决定本地路径。

### Focused workspace

用户最终勾选、出现在主表中的工作群，`selected_group_ids` 本地持久化。

### Export Category

TG Exporter 自己的本地分类，用于落盘：

```text
output_root/category/group/timestamp.json
```

不要把 Export Category 写回 Telegram Chat Folder。

## 6. 当前用户可见能力

- Windows PySide6 GUI，`TG Exporter / TG 导出器`；
- Telegram 登录与 Session 复用；
- Windows system proxy -> Telethon；
- searchable focused workspace；
- Telegram Chat Folder 筛选；
- 42 px 圆形头像 + 约 58 px 双行选择器；
- 软件内 Export Category 管理和每群持久化分类；
- 三种每群独立导出模式；
- frozen unread；
- Option B 每群 `导出后标已读`；
- text/caption-only JSON；
- categorized timestamped atomic JSON；
- migrated Basic Group -> current Supergroup collapse；
- migrated DATE_RANGE history stitching；
- one-file + portable GitHub Releases。

## 7. 关键产品不变量

除非用户再次明确改变：

- 不建设累计 master DB；历史 JSON 不合并、不回写；
- 输出结构：`总输出目录 / 导出分类 / 群组 / 日期时间.json`；
- 每次对某群导出都是独立 JSON；同秒不得覆盖；
- 分类由软件本地管理；删除分类不删除历史文件；
- 聊天消息不下载照片/视频/语音/文件/贴纸；JSON 是权威数据源；
- 群/频道资料头像仅是选择器 UI 例外；
- 每群规则与分类独立；主工作区只显示用户选中的少量群；
- Telegram Chat Folders 只用于选择器筛选，不修改账号分组；
- migrated legacy Basic Group 不重复显示；当前 Supergroup 是主实体；
- 默认导出不改变 Telegram 已读状态；read ack 只有用户按群明确开启且 JSON 成功后才能发送；
- GUI-first；
- 产品名 `TG Exporter / TG 导出器`；AppData 兼容路径继续 `%APPDATA%\TelegramMultiChatExporter\`。

## 8. 当前代码结构

启动链：

```text
launcher.py
→ telegram_exporter.main
→ telegram_exporter.focused_gui.MainWindow
```

GUI 继承：

```text
gui.py
→ gui_async.py
→ focused_gui.py
```

关键模块：

- `category_manager.py`：软件内分类 dialog；
- `export_categories.py`：分类校验/目录/时间戳/同秒冲突；
- `group_selector.py`：Telegram Folder + 搜索 + avatar；
- `telegram_service.py`：catalogue + migration collapse + avatar；
- `exporter.py`：模式查询 + migrated date-range + categorized atomic JSON；
- `read_state.py`：Option B；
- `storage.py`：settings/state atomic JSON；
- `desktop_json.py`：Telegram Desktop-style serializer。

## 9. 未读与已读语义

刷新 catalogue 时冻结：

```text
read_inbox_max_id < id <= latest_message_id
```

`导出后标已读`：

```text
atomic JSON success
→ local checkpoint
→ send_read_acknowledge(max_id=latest_message_id)
```

Telegram read marker 按 ID 推进，所以快照内未进入 JSON 的媒体/系统消息也可能一起已读。migrated legacy history 不参与 current-unread read ack。

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

`settings.json` 主要键：

```text
output_dir
selected_group_ids
mark_read_after_export
export_categories
group_export_categories
```

仓库和日志禁止出现 api_hash、手机号、验证码、2FA、Session 内容、聊天正文、真实头像 cache。

## 11. 当前技术债 / 下一步

- sanitized duplicate group-title folder collision；
- Telegram Desktop chat type / top-level id；
- whitespace 原样保留（当前 `_message_text` 仍 `.strip()`）；
- rich text entities；
- forward/service metadata；
- migrated legacy/current message id 重叠时与 Desktop 的精确语义；
- GUI 三层结构收敛（不得破坏 qasync safety）；
- per-row 实时进度 / retry failed rows。

优先先收集用户对 v0.1.8 的真人验证，再决定是否立即发修复版本。

## 12. v0.1.8 真人验收重点

1. `管理分类` 创建“第一类/第二类”；
2. 总输出目录自动出现分类文件夹；
3. 群1/2 -> 第一类，群3/4/5 -> 第二类，重启仍保存；
4. 导出路径准确为 `分类/群/时间戳.json`；
5. 同日/同秒重复导出不覆盖；
6. 删除软件分类不删除历史文件；
7. 原先出现两遍的迁移群只显示当前 Supergroup 一条；
8. 当前 Supergroup 不消失、不退群、不受修改；
9. 跨迁移日期范围包含旧+新历史；
10. 旧 Session/settings 继续复用。

## 13. 当前不做

除非用户重新提出：360/杀软误报与签名、完整聊天媒体备份、云端消息数据库、自动绕过安全软件。
