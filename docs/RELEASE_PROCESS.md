# Release Process

本文件定义 Windows 正式版本的发布流程。正式用户下载入口是 GitHub Releases，而不是 Actions Artifact。

## 1. 什么时候需要发 Release

需要：

- 用户可见功能变化；
- Telegram 行为变化；
- 影响 EXE 运行的 bug 修复；
- 依赖/打包方式变化；
- 需要用户重新下载验证的修复。

通常不需要：

- 纯文档修改；
- 不影响二进制的注释/说明。

## 2. 发布前状态检查

先读：

- `AGENTS.md`
- `HANDOFF.md`
- `docs/TESTING.md`

确认：

- `main` 包含所有要发布的修复；
- 没有未解决 merge conflict；
- 没有把 Session、API 凭据、日志、聊天导出提交进仓库；
- 新行为已经有回归测试；
- `HANDOFF.md` 已记录需要真人 E2E 的项目。

## 3. 版本号

采用 SemVer 风格：`vMAJOR.MINOR.PATCH`。

发布时至少同步：

1. 根目录 `VERSION`：例如 `v0.1.5`
2. `pyproject.toml` 的 `[project].version`：例如 `0.1.5`
3. 新建 `docs/releases/v0.1.5.md`
4. 更新 `HANDOFF.md` 的“最新正式 Release / main 未发布变更”

不要出现 VERSION 与 pyproject version 不一致。

## 4. 合并前验证

普通 PR 至少通过 `.github/workflows/windows-build.yml`：

```text
Install
pytest -q
GUI import check
PyInstaller one-file build
packaged EXE --smoke-test
Artifact upload
```

涉及 GUI/qasync/Telethon 的变化，必须确认测试覆盖关键回归点；CI smoke-test 只验证打包后可导入/启动 smoke path，不等于真实 Telegram E2E。

## 5. 触发正式 Release

正式 workflow：`.github/workflows/release.yml`。

当前约定：

- push 到 `main`；
- commit message 以 `release:` 开头时自动运行；
- 也支持手动 `workflow_dispatch`，但不要在 VERSION 未更新时随意 dispatch。

推荐发布提交：

```text
release: v0.1.5
```

## 6. Release workflow 必须完成的步骤

正式流水线应全部成功：

```text
Install
Test
GUI import check
Build one-file EXE
Build portable onedir
Smoke-test packaged builds
Prepare release assets
Create or update GitHub Release
```

最终 Release 应包含：

- `TelegramMultiChatExporter-vX.Y.Z-windows-x64.exe`
- `TelegramMultiChatExporter-vX.Y.Z-windows-x64-portable.zip`
- `SHA256SUMS.txt`

若任一 packaged smoke-test 失败，不得把该版本称为可用正式版。

## 7. Release 后核验

检查 GitHub Release：

- tag 正确；
- target commit 正确；
- draft=false；
- prerelease=false（除非用户明确要求预发布）；
- 三个 asset 都存在；
- SHA256SUMS 与 asset 名称对应；
- release notes 描述实际新增能力/修复，不复制过时内容。

正式入口：

```text
https://github.com/3ll3-3ll3/telegram-multi-chat-exporter/releases/latest
```

## 8. 发布后更新交接

发布成功后必须更新 `HANDOFF.md`：

- 最新 Release 版本；
- release target commit；
- 哪些修复已进入正式版；
- `main` 是否又有未发布提交；
- 哪些项目等待用户真实环境验证。

如果用户验证成功/失败，也要继续更新 HANDOFF，而不是只留在聊天记录里。

## 9. Hotfix 原则

如果用户上传截图/日志定位到明确 bug：

1. 先判断是已发布版本 bug 还是 main 已修未发布。
2. 修复写回归测试。
3. Windows CI 绿。
4. 若影响用户实际使用，尽快发 PATCH Release。
5. 不把多个未经验证的大功能硬塞进紧急 hotfix。

## 10. 当前特别注意

截至 2026-08-28，正式 Release 为 v0.1.4，而 `main` 已有 shutdown/disconnect 修复且 Windows CI 通过但未发布。接手 Agent 应以 `HANDOFF.md` 的当前状态为准，不要误以为 v0.1.4 已包含该退出 hotfix。
