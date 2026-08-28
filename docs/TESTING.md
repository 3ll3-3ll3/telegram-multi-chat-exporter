# Testing guide

## First Windows test

1. Download the `TelegramMultiChatExporter-windows-x64` artifact from GitHub Actions.
2. Extract `TelegramMultiChatExporter.exe` and launch it normally; no command line is required.
3. On first launch, enter your own Telegram `api_id` and `api_hash`, then complete phone/code/2FA login if requested.
4. Select a small set of groups and give each group an independent rule (date range, unread, or since-last after a prior successful export).
5. Confirm that every selected group receives its own `result.json` inside one independent batch directory.
6. Confirm that no media files are downloaded.

## Security checks

Runtime credentials, the Telethon session, checkpoints, and exported chat content must remain under the user's local machine. Never commit these files to this public repository.

## V0.1 validation targets

- Mixed-mode export across five groups.
- Inclusive local-date boundary behavior.
- Unread-mode behavior against Telegram's read marker.
- Same-window comparison against Telegram Desktop JSON for plain-text messages.
- Windows x64 PyInstaller artifact launches successfully.
