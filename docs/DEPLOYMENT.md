# Deployment / Distribution

TG Exporter 当前没有服务器部署。本文中的“部署”是：**从源码构建 Windows 二进制、生成 Candidate、发布 GitHub Release，以及必要时回滚到历史 Release。**

## 1. 环境

主要目标：Windows x64。

开发/CI 当前使用：

- Python 3.13；
- PySide6；
- Telethon；
- qasync；
- python-socks；
- PyInstaller；
- pytest。

依赖以 `pyproject.toml` 为准，不要只依赖本文版本描述。

## 2. 本地开发

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
pytest -q
```

GUI source run：

```powershell
python -m telegram_exporter
```

CLI source run：

```powershell
python -m telegram_exporter.tgctl status --json
```

v0.3 daemon/reader 的准确命令和实现只在 PR #20 分支，接手时先核对该 PR。

## 3. 用户本地运行数据不是部署资产

GitHub Release **不得**包含：

```text
%APPDATA%\TelegramMultiChatExporter\api_credentials.json
%APPDATA%\TelegramMultiChatExporter\telegram.session
settings/local_state/job metadata
logs
avatar cache
用户导出 JSON
```

升级版本继续复用该 AppData 路径；不要通过 installer/build 流程搬迁或清空用户数据。

## 4. Windows CI Candidate

开发分支/PR 使用 `.github/workflows/windows-build.yml`。

v0.3 Candidate 当前最低 gate：

```text
pip install -e ".[dev]"
pytest -q
GUI + daemon + reader + CLI import
TGExporter one-file build
TGExporter portable onedir build
tgctl one-file build
standalone + portable SESSION_BUSY JSON/native exit=8 regression
one-file + portable GUI smoke
standalone + portable tgctl smoke
candidate SHA-256
Actions artifact upload
```

Candidate Artifact 是临时验收产物，不是正式下载入口。

截至 2026-08-30，真人 E2E 固定 runtime candidate：

```text
commit: 0ad4219ef367d28326b5aca705fffe1d007db52b
Windows run: 33293667296
artifact: 9726786295
pytest: 91 passed
```

完整 hash 见 `HANDOFF.md`。

## 5. 正式 Release 流程

正式发布只走 GitHub Releases。

```text
latest main
→ feature/fix branch
→ tests
→ PR
→ Windows CI green
→ required human E2E
→ user explicit release authorization
→ merge/release commit
→ formal release workflow
→ verify Release
```

当前 workflow 约定：用户可见二进制版本的 main head commit 使用：

```text
release: vX.Y.Z
```

或在确认版本文件正确后人工 `workflow_dispatch`。

正式 workflow 必须构建：

```text
TGExporter-vX.Y.Z-windows-x64.exe
TGExporter-vX.Y.Z-windows-x64-portable.zip
tgctl.exe
SHA256SUMS.txt
```

Portable ZIP 内包含 TGExporter onedir 与 `tgctl.exe`。

## 6. 版本文件一致性

正式发布时同步：

```text
VERSION
pyproject.toml [project].version
src/telegram_exporter/__init__.py __version__
docs/releases/vX.Y.Z.md
HANDOFF.md
```

不得出现代码版本、VERSION、Release tag 三者不一致。

## 7. Release 前最低验证

除单元/打包测试外必须确认：

- 没有 Secret/Session/聊天正文进入 repo/CI；
- v0.1.10+ packaged UTF-8 `SESSION_BUSY` native exit=8 regression 保留；
- one-file 与 portable 都 smoke；
- tgctl standalone 与 portable 都 smoke；
- Telegram write safety 未绕过；
- HANDOFF 明确哪些是 CI/mock，哪些是真人 E2E；
- Release notes 描述当前真实行为。

v0.3 额外硬闸门：**用户真人 Telegram E2E PASS + 用户明确授权发布**。

## 8. Release 后核验

只有以下全部满足才能宣称“已发布”：

```text
correct tag
correct target commit
draft=false
prerelease=false
all expected assets exist
SHA256SUMS matches assets
release notes match behavior
release workflow conclusion=success
```

然后更新 `HANDOFF.md`：正式版本、commit、PR、workflow、asset hashes、真人 E2E 状态。

## 9. Rollback

本项目没有数据库 rollback。二进制回滚方式是：

1. 从 GitHub Releases 下载上一个已验证版本；
2. 保留 `%APPDATA%\TelegramMultiChatExporter\`；
3. 不删除/重建 `telegram.session`；
4. 使用旧版本前确认新版本没有引入不可逆本地 schema 迁移。

当前设计要求本地状态尽量向后兼容；如未来确实加入不可逆 schema migration，必须先在 ADR + HANDOFF + Release Notes 明确备份/回滚策略，不能静默执行。

## 10. v0.3 Candidate → Release

当前恢复路径：

```text
PR #20 remains Draft
→ user runs frozen Candidate E2E
→ failures: fix + regression + CI + affected E2E
→ all PASS: record E2E in HANDOFF/PR
→ finalize docs/releases/v0.3.0.md
→ user explicitly authorizes release
→ merge/release to main
→ formal Release workflow
→ verify assets + hashes
```

在用户授权之前，禁止创建或覆盖 `v0.3.0` Release。

## 11. No cloud deployment

不要创建 Cloudflare Worker、VPS、Web API、remote DB、Windows Service 或开机常驻服务来“部署”当前项目。v0.3 daemon 是本机按需启动的用户态进程，约 10 分钟空闲自动退出；它不是云端/系统级生产服务。