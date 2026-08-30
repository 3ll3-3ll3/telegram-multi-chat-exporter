# Deployment / Release Guide

TG Exporter 没有云端部署。Production deployment = GitHub Release Windows binaries。

## Build inputs

- Python 3.13；
- `pip install -e ".[dev]"`；
- VERSION 必须是 `vX.Y.Z`；
- `docs/releases/<VERSION>.md` 必须存在。

## Candidate gate

Runtime PR 至少通过：

```text
pytest -q
GUI + daemon + reader + tgctl import
TGExporter one-file PyInstaller
TGExporter portable onedir
tgctl one-file
standalone + portable SESSION_BUSY JSON/native exit 8
one-file + portable GUI smoke
standalone + portable tgctl smoke
candidate hashes/artifact
```

Candidate Artifact 只用于验收，不是正式分发物。

## Formal release

1. 用户可见 release notes 收尾；
2. final PR head CI green；
3. merge 到 main，release commit message 以 `release:` 开头；
4. `.github/workflows/release.yml` 自动执行；
5. workflow 重新测试并重新构建 one-file/portable/tgctl；
6. 生成 `SHA256SUMS.txt`；
7. 创建 GitHub Release/tag；
8. 人工核验 Release 实体、target commit、四个 assets、hash；
9. 更新 HANDOFF Production 状态。

## v0.3.0 reference

```text
main/tag target: 8e230e33ea928bcf71296e4e5379b097446dbec5
Release workflow: 33299040904 = success
Release: https://github.com/3ll3-3ll3/tg-exporter/releases/tag/v0.3.0
```

## Rollback

不要删除或覆盖新旧 Release。若 v0.3.0 出现严重问题：

1. 先建立 Issue 并停止继续扩大问题；
2. 用户可临时下载上一正式 Release；
3. 不删除 `%APPDATA%\TelegramMultiChatExporter\`，避免破坏 Session/settings/checkpoints；
4. 做最小 patch branch → PR → CI → 新 patch Release；
5. 不重写已有 tag，不用 force-push 模拟 rollback。

正式 rollback 是“选择上一已发布 binary + 发布新的修复版本”，不是改写历史。
