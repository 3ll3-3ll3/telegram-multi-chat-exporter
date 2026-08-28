# Release Process

本文件定义 TG Exporter Windows 正式版本的发布流程。正式用户下载入口是 GitHub Releases，而不是 Actions Artifact。

## 1. 什么时候需要发 Release

需要：用户可见功能变化、Telegram 行为变化、影响 EXE 运行的 bug 修复、依赖/打包方式变化、需要用户重新下载验证的修复。

通常不需要：纯文档修改、不影响二进制的注释/说明。

## 2. 发布前状态检查

先读 `AGENTS.md`、`HANDOFF.md`、`docs/TESTING.md`。确认 main/待合并分支没有冲突，没有 Session/API 凭据/日志/聊天导出进入仓库，新行为有回归测试，HANDOFF 已记录真人 E2E 待办。

## 3. 版本号

采用 SemVer 风格：`vMAJOR.MINOR.PATCH`。

发布时同步：

1. 根目录 `VERSION`，例如 `v0.1.6`；
2. `pyproject.toml` 的 `[project].version`，例如 `0.1.6`；
3. 新建 `docs/releases/v0.1.6.md`；
4. 更新 `HANDOFF.md`。

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

CI smoke-test 不等于真实 Telegram E2E。

## 5. 触发正式 Release

正式 workflow：`.github/workflows/release.yml`。

- push 到 `main`；
- commit message 以 `release:` 开头时自动运行；
- 也支持 `workflow_dispatch`，但不要在 VERSION 未更新时随意 dispatch。

推荐提交：

```text
release: v0.1.6
```

## 6. Release workflow 必须完成

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

从 v0.1.6 起，正式资产名为：

- `TGExporter-vX.Y.Z-windows-x64.exe`
- `TGExporter-vX.Y.Z-windows-x64-portable.zip`
- `SHA256SUMS.txt`

PyInstaller 内部入口名同样使用 `TGExporter`。若任一 packaged smoke-test 失败，不得把该版本称为可用正式版。

## 7. Release 后核验

检查：tag、target commit、draft=false、prerelease=false、三个 asset 存在、SHA256SUMS 与资产名一致、release notes 与实际版本一致。

固定入口：

```text
https://github.com/3ll3-3ll3/telegram-multi-chat-exporter/releases/latest
```

## 8. 发布后更新交接

发布成功后必须更新 `HANDOFF.md`：最新版、target commit、正式进入的能力/修复、main 是否还有未发布提交、真人验证待办。

## 9. Hotfix 原则

明确 bug → 回归测试 → Windows CI → 影响用户实际使用则尽快 PATCH Release；不要把多个未经验证的大功能硬塞进紧急 hotfix。

## 10. 品牌与兼容路径

从 v0.1.6 起产品名为 **TG Exporter / TG 导出器**，EXE 为 `TGExporter.exe`。

内部 Python module `telegram_exporter` 和历史运行时目录 `%APPDATA%\TelegramMultiChatExporter\` 保持不变，以避免升级后 Session、API 设置和本地状态失效。
