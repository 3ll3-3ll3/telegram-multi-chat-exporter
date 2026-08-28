from __future__ import annotations

import os
from pathlib import Path

APP_DIR_NAME = "TelegramMultiChatExporter"


def app_data_dir() -> Path:
    base = os.environ.get("APPDATA")
    if base:
        path = Path(base) / APP_DIR_NAME
    else:
        path = Path.home() / ".telegram-multi-chat-exporter"
    path.mkdir(parents=True, exist_ok=True)
    return path


def credentials_path() -> Path:
    return app_data_dir() / "api_credentials.json"


def session_path() -> Path:
    return app_data_dir() / "telegram"


def state_path() -> Path:
    return app_data_dir() / "local_state.json"


def settings_path() -> Path:
    return app_data_dir() / "settings.json"
