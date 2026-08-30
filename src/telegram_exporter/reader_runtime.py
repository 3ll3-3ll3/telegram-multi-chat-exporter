from __future__ import annotations

from typing import Any

from .reader_models import DialogInfo, ParticipantInfo
from .reader_service import PersonalAccountReader, _safe_peer_id


class PersonalAccountReaderV3(PersonalAccountReader):
    """Production reader with logical-chat identity fixes layered on core tests."""

    async def _admin_snapshot(
        self,
        row: DialogInfo,
        entity: Any,
    ) -> tuple[dict[int, ParticipantInfo], bool]:
        # Historical messages may come from a legacy Basic Group while the
        # logical chat is the current Supergroup. Current owner/admin role must
        # always be evaluated on the current logical entity, never by passing a
        # legacy Chat into channels.getParticipants.
        if row.dialog_type in {"group", "supergroup", "channel"}:
            source_id = _safe_peer_id(entity)
            if source_id is not None and source_id != row.chat_id:
                try:
                    entity = await self.client.get_entity(row.chat_id)
                except Exception:
                    return {}, False
        return await super()._admin_snapshot(row, entity)
