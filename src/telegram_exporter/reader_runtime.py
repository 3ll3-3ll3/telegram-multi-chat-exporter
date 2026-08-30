from __future__ import annotations

from typing import Any

from telethon.tl.custom.message import Message

from .bridge_errors import INVALID_ARGUMENT, MESSAGE_NOT_FOUND, TelegramBridgeError
from .reader_models import DialogInfo, MessageInfoV3, ParticipantInfo
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

    async def messages_get_v3(self, chat: str | int, ids: list[int]) -> list[MessageInfoV3]:
        """Fetch exact messages while preserving logical/current migration identity.

        When callers use a history row's ``source_chat_id`` for a legacy Basic
        Group, Telegram must read the message from that legacy peer, but the rich
        schema should still expose the current Supergroup as ``chat_id`` and the
        legacy peer as ``source_chat_id``. This keeps get/history/search mutually
        consistent and avoids message-id ambiguity across migration segments.
        """

        requested = tuple(dict.fromkeys(int(value) for value in ids))
        if not requested:
            raise TelegramBridgeError(INVALID_ARGUMENT, "至少需要一个 message_id。")

        source_row, source_entity = await self.resolve_dialog(chat)
        logical_row = source_row
        source_chat_id = source_row.chat_id
        if source_row.migrated_to_chat_id is not None:
            try:
                logical_row, _ = await self.resolve_dialog(source_row.migrated_to_chat_id)
            except TelegramBridgeError:
                # If Telegram no longer resolves the current side, retain the
                # source row rather than guessing a logical identity.
                logical_row = source_row

        messages = await self.client.get_messages(source_entity, ids=list(requested))
        by_id = {
            int(message.id): message
            for message in (messages or ())
            if isinstance(message, Message)
        }
        missing = [message_id for message_id in requested if message_id not in by_id]
        if missing:
            raise TelegramBridgeError(
                MESSAGE_NOT_FOUND,
                "部分消息不存在或当前账号无权访问。",
                {"missing_ids": missing, "reason": "not_found_or_unavailable"},
            )

        role_snapshot, role_available = (
            await self._admin_snapshot(logical_row, source_entity)
            if logical_row.dialog_type in {"group", "supergroup", "channel"}
            else ({}, False)
        )
        return [
            await self._message_info_v3(
                logical_row,
                source_chat_id,
                by_id[message_id],
                role_snapshot,
                role_available,
            )
            for message_id in requested
        ]
