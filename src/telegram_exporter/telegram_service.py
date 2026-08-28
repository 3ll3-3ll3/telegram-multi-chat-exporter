from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.utils import get_peer_id

from .models import GroupInfo

logger = logging.getLogger("telegram_exporter.telegram_service")


@dataclass(slots=True)
class ApiCredentials:
    api_id: int
    api_hash: str


class TelegramService:
    def __init__(self, credentials: ApiCredentials, session_file: Path):
        self.client = TelegramClient(str(session_file), credentials.api_id, credentials.api_hash)
        logger.info("Telegram client initialized (api_id=%s, session=%s)", credentials.api_id, session_file.name)

    async def connect(self) -> bool:
        logger.info("Connecting to Telegram transport")
        try:
            await self.client.connect()
            authorized = await self.client.is_user_authorized()
            logger.info("Telegram transport connected; authorized=%s", authorized)
            return authorized
        except Exception:
            logger.exception("Telegram transport connection failed")
            raise

    async def send_code(self, phone: str) -> None:
        logger.info("Requesting Telegram login code")
        try:
            await self.client.send_code_request(phone)
            logger.info("Telegram login code request accepted")
        except Exception:
            logger.exception("Telegram login code request failed")
            raise

    async def sign_in_code(self, phone: str, code: str) -> bool:
        logger.info("Submitting Telegram login code")
        try:
            await self.client.sign_in(phone=phone, code=code)
        except SessionPasswordNeededError:
            logger.info("Telegram account requires 2FA password")
            return False
        except Exception:
            logger.exception("Telegram login code verification failed")
            raise
        logger.info("Telegram login code verified")
        return True

    async def sign_in_password(self, password: str) -> None:
        logger.info("Submitting Telegram 2FA password")
        try:
            await self.client.sign_in(password=password)
            logger.info("Telegram 2FA verification succeeded")
        except Exception:
            logger.exception("Telegram 2FA verification failed")
            raise

    async def list_groups(self) -> list[GroupInfo]:
        logger.info("Loading Telegram dialogs")
        groups: list[GroupInfo] = []
        try:
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
        except Exception:
            logger.exception("Loading Telegram dialogs failed")
            raise
        groups.sort(key=lambda x: x.title.casefold())
        logger.info("Loaded %s groups/channels", len(groups))
        return groups

    async def close(self) -> None:
        if self.client.is_connected():
            logger.info("Disconnecting Telegram client")
            await self.client.disconnect()
