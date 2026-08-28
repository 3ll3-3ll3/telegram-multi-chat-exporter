from __future__ import annotations

import asyncio

from telegram_exporter.exporter import export_group
from telegram_exporter.models import ExportMode, GroupExportPlan, GroupInfo


class FakeClient:
    def __init__(self):
        self.kwargs = None

    async def get_entity(self, chat_id):
        return chat_id

    def iter_messages(self, entity, **kwargs):
        self.kwargs = kwargs

        async def empty():
            if False:
                yield None

        return empty()


def test_unread_export_uses_snapshot_bounds(tmp_path):
    client = FakeClient()
    group = GroupInfo(
        chat_id=-100123,
        title="Example",
        unread_count=15,
        read_inbox_max_id=40,
        latest_message_id=55,
    )
    plan = GroupExportPlan(group=group, mode=ExportMode.UNREAD)

    result = asyncio.run(export_group(client, plan, tmp_path))

    assert result.message_count == 0
    assert client.kwargs == {"reverse": True, "min_id": 40, "max_id": 56}
