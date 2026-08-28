# Roadmap

## V0.1 repository preview

- [x] PySide6 GUI main table
- [x] Per-group export mode
- [x] Date range / unread / since-last modes in model
- [x] Pure-text export path
- [x] Independent batch directories
- [x] Desktop-style JSON serializer
- [x] Local-only state and credential paths
- [x] Windows GitHub Actions EXE build
- [x] Unit tests for serializer/state/model
- [x] First-login phone/code/2FA GUI wizard
- [ ] Real Telegram account E2E validation
- [ ] Official Telegram Desktop result.json differential test
- [ ] Per-row live progress + retry failed rows
- [ ] Rich text entity mapping parity

## V0.2 daily-test candidate

投入个人日常测试前必须完成：

1. First-login GUI wizard.
2. Five-group mixed-mode E2E test.
3. Date boundary test (inclusive local dates).
4. Unread-mode verification against Telegram client read markers.
5. Same-window comparison with official Telegram Desktop JSON.
6. GitHub Actions artifact successfully builds on Windows.
