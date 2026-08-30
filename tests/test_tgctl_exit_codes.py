from __future__ import annotations

import json

from telegram_exporter import tgctl
from telegram_exporter.session_lock import SessionBusyError


def test_session_busy_returns_exit_code_8(monkeypatch, capsys) -> None:
    async def fake_run(_args):
        raise SessionBusyError("session busy for test")

    monkeypatch.setattr(tgctl, "setup_logging", lambda: None)
    monkeypatch.setattr(tgctl, "run_command", fake_run)

    code = tgctl.main(["status", "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert captured.err == ""
    assert code == 8
    assert payload["ok"] is False
    assert payload["error"]["code"] == "SESSION_BUSY"
