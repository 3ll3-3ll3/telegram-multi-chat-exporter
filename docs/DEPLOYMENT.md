# Deployment / Distribution

TG Exporter 当前没有服务器部署。这里的“部署”仅指：**构建 Windows 二进制、生成 Candidate、发布 GitHub Release、以及必要时回滚到历史 Release。**

## 1. 当前 Production

```text
Release: v0.3.0
commit: 8e230e33ea928bcf71296e4e5379b097446dbec5
```

当前修复线：

```text
branch: codex/v0.3.1-runtime-fixes
PR: #24 (Draft until local human acceptance passes)
```

`v0.3.0` tag/Release 不得移动、覆盖、删除或原地重建。

## 2. 目标环境

主要目标 Windows x64。依赖以 `pyproject.toml` 为准；当前 CI 使用 Python 3.13、PySide6、Telethon、qasync、python-socks、PyInstaller、pytest。

本地开发：

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
pytest -q
python -m telegram_exporter
python -m telegram_exporter.tgctl status --json
```

## 3. 用户本地运行数据不是发布资产

Release / CI artifact 永远不得包含：

```text
%APPDATA%\TelegramMultiChatExporter\api_credentials.json
%APPDATA%\TelegramMultiChatExporter\telegram.session
session journal/lock
ipc identity/auth secret
settings/local_state/job metadata
logs/avatar cache
用户导出 JSON
```

升级继续复用既有 AppData 路径；不要为安装/修复而清空、迁移或复制 Session。

## 4. Candidate CI

开发分支/PR 使用 `.github/workflows/windows-build.yml`。v0.3.1 的完整 gate 包括：

```text
full pytest
focused v0.3.1 regressions
compileall
git diff --check
GUI + daemon + reader + CLI imports
source search-filter smoke
TGExporter one-file PyInstaller
TGExporter portable onedir PyInstaller
tgctl one-file PyInstaller
standalone + portable packaged domain+regex smoke
standalone + portable SESSION_BUSY JSON/native exit=8
packaged GUI/tgctl smoke
tracked-worktree clean
candidate SHA-256
Actions artifact upload
```

Candidate Artifact 只用于验收，不是正式分发入口。Candidate hash 与正式 Release rebuild hash 可以不同。

当前 v0.3.1 最终证据以 PR #24 当前 body / latest CI 为准；不要从旧 Candidate 文档猜状态。

## 5. 正式 Release 流程

```text
main
→ issue/fix branch
→ tests
→ PR
→ Windows CI green
→ required local Windows / real-account acceptance
→ user explicit merge/release authorization
→ merge to main
→ Release workflow rebuild
→ verify Release/tag/assets/SHA
```

不得直接 push/force-push main。不得覆盖任何历史 tag/Release。

正式 Release 资产应包括：

```text
TGExporter-vX.Y.Z-windows-x64.exe
TGExporter-vX.Y.Z-windows-x64-portable.zip
tgctl.exe
SHA256SUMS.txt
```

Portable ZIP 内应包含与已验证 standalone 相同版本的 `tgctl.exe`。

## 6. Release 前/后验证

发布前至少确认：

- `VERSION` / `pyproject.toml` / package `__version__` / Release tag 一致；
- no secrets/session/chat-body in repo/CI;
- one-file + portable + tgctl builds/smokes pass；
- packaged search-filter smoke pass；
- legacy lock → `SESSION_BUSY` + native exit 8；
- write safety / no-auto-retry invariant 未破坏；
- required human acceptance 已明确 PASS；
- Release notes 与真实行为一致。

只有以下全部满足才能说“已发布”：

```text
correct tag
correct target commit
draft=false
prerelease=false
expected assets exist
SHA256SUMS matches assets
release workflow conclusion=success
release notes match behavior
```

## 7. v0.3.1 当前发布边界

v0.3.1 自动化 Candidate 可以生成，但在用户本机/真实账号验收和明确授权之前：

- PR #24 保持 Draft；
- 不 merge；
- 不创建 v0.3.1 tag/Release；
- 不修改 v0.3.0。

默认真人验收不执行 real send/forward、mark-read、confirmed media download、group mutation、FloodWait stress 或 Session reset。

## 8. Rollback

本项目无远程数据库 rollback。二进制回滚：

1. 从 GitHub Releases 下载上一个已验证版本；
2. 保留 `%APPDATA%\TelegramMultiChatExporter\`；
3. 不删除/重建 `telegram.session`；
4. 若未来出现不可逆本地 schema migration，必须提前用 ADR/HANDOFF/Release Notes 描述备份与回滚。

## 9. No cloud deployment

不要为当前项目创建 Cloudflare Worker、VPS、Web API、remote DB、Windows Service 或 24/7 server。daemon 是本机按需用户态进程，不是云服务。