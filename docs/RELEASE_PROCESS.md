# Release Process

TG Exporter 正式用户下载入口是 **GitHub Releases**，不是 Actions Artifact。Windows build / Candidate / rollback 的可执行步骤同时见 [`DEPLOYMENT.md`](DEPLOYMENT.md)。

## 1. Production vs Candidate

- Production：已发布 GitHub Release；
- Candidate：Actions Artifact，仅供测试/真人验收；
- `main` 是正式线；开发分支/PR 可以包含未发布的下一代架构。

截至 2026-08-30，Production 为 v0.1.10；v0.3.0 在 Draft PR #20 中，尚未发布。实时值以 `HANDOFF.md` + GitHub 为准。

## 2. 什么时候需要 Release

需要：用户可见 runtime 功能、Telegram 行为、EXE/tgctl bug、依赖/打包方式发生需要用户重新下载的变化。

通常不需要：纯文档/注释且二进制行为不变。

## 3. 发布前恢复/安全检查

先读：

```text
AGENTS.md
HANDOFF.md
docs/ARCHITECTURE.md
docs/SECURITY_MODEL.md
SECURITY.md
docs/DECISIONS.md
docs/TESTING.md
docs/DEPLOYMENT.md
```

再核对 GitHub 当前：main、开发 branch、PR、CI、Latest Release/Tag。

确认：

- feature/fix 来自正确正式基线；
- 没有遗漏 integration conflict；
- 没有 Session/credentials/聊天正文进入 repo/CI；
- 新行为有 regression；
- HANDOFF 区分 automated vs human E2E；
- Telegram write safety 未弱化；
- 没有覆盖/移动历史 Release/tag；
- 用户要求的 human release gate 已满足。

## 4. 版本号

正式发布同步：

```text
VERSION
pyproject.toml [project].version
src/telegram_exporter/__init__.py __version__
docs/releases/vX.Y.Z.md
HANDOFF.md
```

不得让 VERSION / package / tag / Release notes 互相矛盾。

## 5. 分支 / PR

标准流程：

```text
latest main
→ feature/fix branch
→ tests
→ PR
→ Windows CI green
→ required human E2E
→ explicit release approval where required
→ merge
```

不得为发版直接堆未经 PR/CI 的功能代码到 main；不得 force-push main。

当前仓库无 branch protection，所以这属于 Agent 必须自行执行的政策。

## 6. Windows PR CI

当前 Windows runtime 最低理念：

```text
pytest
import checks
PyInstaller one-file
portable where release parity matters
tgctl build
native exit-code regressions
packaged smoke
artifact/hash
```

v0.3 Candidate 的精确 gate 和当前 frozen artifact 在 `docs/TESTING.md` / `HANDOFF.md`。

## 7. Formal Release workflow

`.github/workflows/release.yml` 在符合 workflow 条件的 `release:` main commit 或明确 `workflow_dispatch` 时运行。

正式 Release 至少构建：

```text
TGExporter-vX.Y.Z-windows-x64.exe
TGExporter-vX.Y.Z-windows-x64-portable.zip
tgctl.exe
SHA256SUMS.txt
```

并 smoke-test one-file/portable GUI、standalone/portable tgctl。

v0.1.10+ 必须保留 packaged UTF-8 `SESSION_BUSY` JSON + native exit=8 regression，包括 standalone 与 portable tgctl。

## 8. Release notes

Workflow 从：

```text
docs/releases/<VERSION>.md
```

读取 notes。Notes 描述当前实际 binary，不复制陈旧能力。

涉及 tgctl/reader 时至少明确：

- 新命令/语义；
- read vs write；
- dry-run/caps；
- Session/daemon model；
- human E2E 已做/未做；
- out-of-scope safety boundary。

## 9. v0.3 hard release gate

v0.3 不采用“CI green 就直接发布”。固定：

```text
Automated Candidate gate green
→ frozen hash-traceable Candidate
→ user real Telegram E2E
→ fix only actual failures + rerun affected checks
→ human E2E PASS
→ user explicitly authorizes release
→ finalize Release Notes
→ merge/release
```

在真人 E2E PASS + 用户明确授权前：

- PR #20 保持 Draft；
- 不 merge；
- 不创建/覆盖 `v0.3.0` Release；
- 不继续加入无关功能；
- Candidate Artifact 不称为正式版。

ADR：[`006-human-e2e-release-gate.md`](decisions/006-human-e2e-release-gate.md)。

## 10. GitHub Actions 与真实 Telegram

Actions 不使用用户真实 Telegram credentials。

Telegram API/write tests 使用 mock/fake/local lock。真实账号 E2E 在用户本机做：

- read-first；
- write 先 dry-run；
- 用户明确确认后再真实写；
- 优先 Saved Messages；
- 不故意制造 FloodWait；
- media download 只有用户明确选择才产生本地文件。

## 11. 正式 Release 后核验

只有全部满足才能说“已发布”：

```text
correct tag
correct target commit
draft=false
prerelease=false
all expected assets exist
SHA256SUMS matches assets
Release notes match behavior
formal workflow success
```

随后更新 `HANDOFF.md`：Production version/commit、PR、workflow、asset hashes、main 未发布状态、human E2E 状态。

## 12. Rollback

本项目没有生产数据库 rollback。回滚是使用上一正式 Release，同时保留 `%APPDATA%\TelegramMultiChatExporter\`。

不得通过删除 Session/settings 进行回滚。未来若出现不可逆本地 schema migration，必须事先有 ADR、备份/兼容/rollback 说明。

详见 [`DEPLOYMENT.md`](DEPLOYMENT.md)。

## 13. Hotfix

明确 bug → regression → Windows CI → 影响实际使用则 PATCH Release。

Hotfix 不混入未验证的大型架构重写。v0.1.10 就是这一原则的例子：只修 packaged UTF-8/exit-code contract，并把 regression forward-port 到下一代。

## 14. Branding / compatibility path

用户可见：`TG Exporter / TG 导出器`、`TGExporter.exe`、`tgctl.exe`。

内部 Python package：`telegram_exporter`。

兼容 AppData 永远保持：

```text
%APPDATA%\TelegramMultiChatExporter\
```

Release/install/build 不得擅自迁移或清空该目录。