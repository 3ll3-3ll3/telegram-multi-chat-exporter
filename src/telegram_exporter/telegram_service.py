from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.utils import get_peer_id

from .models import GroupInfo


@dataclass(slots=True)
class ApiCredentials:
    api_id: int
    api_hash: str


class TelegramService:
    def __init__(self, credentials: ApiCredentials, session_file: Path):
        self.client = TelegramClient(str(session_file), credentials.api_id, credentials.api_hash)

    async def connect(self) -> bool:
        await self.client.connect()
        return await self.client.is_user_authorized()

    async def send_code(self, phone: str) -> None:
        await self.client.send_code_request(phone)

    async def sign_in_code(self, phone: str, code: str) -> bool:
        try:
            await self.client.sign_in(phone=phone, code=code)
        except SessionPasswordNeededError:
            return False
        return True

    async def sign_in_password(self, password: str) -> None:
        await self.client.sign_in(password=password)

    async def list_groups(self) -> list[GroupInfo]:
        groups: list[GroupInfo] = []
        async for dialog in self.client.iter_dialogs():
            if not (dialog.is_group or dialog.is_channel):
                continue
            entity = dialog.entity
            groups.append(
                GroupInfo(
                    chat_id=int(get_peer_id(entity)),
                    title=dialog.name or str(get_peer_id(entity)),
                    username=getattr(entity, "username", None),
                    unread_count=int(dialog.unread_count or 0),
                    read_inbox_max_id=int(getattr(dialog.dialog, "read_inbox_max_id", 0) or 0),
                )
            )
        groups.sort(key=lambda x: x.title.casefold())
        return groups

    async def close(self) -> None:
        if self.client.is_connected():
            await self.client.disconnect()
