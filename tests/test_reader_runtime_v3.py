from __future__ import annotations

import asyncio
from types import SimpleNamespace

from telegram_exporter.cursor_codec import CursorCodec
from telegram_exporter.reader_models import DialogInfo
from telegram_exporter.reader_runtime import PersonalAccountReaderV3
from telegram_exporter.reader_service import PersonalAccountReader

CURRENT_ID = -(10**12 + 77)
LEGACY_ID = -77


class FakeClient:
    def __init__(self):
        self.requested = []

    async def get_entity(self, value):
        self.requested.append(value)
        return CURRENT_ID


def test_migrated_source_uses_current_logical_entity_for_role_snapshot(monkeypatch) -> None:
    client = FakeClient()
    reader = PersonalAccountReaderV3(SimpleNamespace(client=client), cursor_codec=CursorCodec(b"r" * 32))
    row = DialogInfo(
        chat_id=CURRENT_ID,
        title="Current supergroup",
        username=None,
        dialog_type="supergroup",
        migrated_from_chat_id=LEGACY_ID,
    )
    seen = {}

    async def fake_base_snapshot(_self, received_row, entity):
        seen["row"] = received_row
        seen["entity"] = entity
        return {}, True

    monkeypatch.setattr(PersonalAccountReader, "_admin_snapshot", fake_base_snapshot)
    snapshot, available = asyncio.run(reader._admin_snapshot(row, LEGACY_ID))

    assert snapshot == {}
    assert available is True
    assert client.requested == [CURRENT_ID]
    assert seen["row"] is row
    assert seen["entity"] == CURRENT_ID
