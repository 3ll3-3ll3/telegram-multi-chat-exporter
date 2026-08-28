from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from telethon.tl import functions
from telethon.utils import get_peer_id

from .dialog_filters import apply_folder_memberships
from .models import GroupInfo
from .proxy import ProxyConfig, detect_windows_system_proxy

logger = logging.getLogger("telegram_exporter.telegram_service")


@dataclass(slots=True)
class ApiCredentials:
    api_id: int
    api_hash: str


def _dialog_is_muted(dialog) -> bool:
    settings = getattr(getattr(dialog, "dialog", None), "notify_settings", None)
    mute_until = getattr(settings, "mute_until", None)
    if not mute_until:
        return False
    if isinstance(mute_until, datetime):
        if mute_until.tzinfo is None:
            mute_until = mute_until.replace(tzinfo=timezone.utc)
        return mute_until > datetime.now(timezone.utc)
    try:
        return float(mute_until) > datetime.now(timezone.utc).timestamp()
    except (TypeError, ValueError):
        return False


class TelegramService:
    def __init__(self, credentials: ApiCredentials, session_file: Path):
        self.proxy: ProxyConfig | None = detect_windows_system_proxy()
        proxy_payload = self.proxy.as_telethon_dict() if self.proxy else None
        self.client = TelegramClient(
            str(session_file),
            credentials.api_id,
            credentials.api_hash,
            proxy=proxy_payload,
        )
        logger.info(
            "Telegram client initialized (api_id=%s, session=%s, proxy=%s)",
            credentials.api_id,
            session_file.name,
            self.proxy.safe_label if self.proxy else "direct",
        )

    async def connect(self) -> bool:
        logger.info(
            "Connecting to Telegram transport via %s",
            self.proxy.safe_label if self.proxy else "direct connection",
        )
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
                unread_count = int(dialog.unread_count or 0)
                unread_mark = bool(getattr(dialog.dialog, "unread_mark", False))
                groups.append(
                    GroupInfo(
                        chat_id=int(get_peer_id(entity)),
                        title=dialog.name or str(get_peer_id(entity)),
                        username=getattr(entity, "username", None),
                        unread_count=unread_count,
                        read_inbox_max_id=int(getattr(dialog.dialog, "read_inbox_max_id", 0) or 0),
                        latest_message_id=int(getattr(dialog.message, "id", 0) or 0),
                        is_group=bool(dialog.is_group),
                        is_broadcast=bool(dialog.is_channel and not dialog.is_group),
                        is_muted=_dialog_is_muted(dialog),
                        is_archived=bool(getattr(dialog, "archived", False)),
                        is_unread=bool(unread_count > 0 or unread_mark),
                    )
                )
        except Exception:
            logger.exception("Loading Telegram dialogs failed")
            raise

        # Telegram calls account-side chat folders "dialog filters". Folder
        # loading is deliberately non-fatal: if the API/schema ever changes,
        # the existing all-groups selector must still remain usable.
        try:
            response = await self.client(functions.messages.GetDialogFiltersRequest())
            filters = getattr(response, "filters", response)
            folder_count = apply_folder_memberships(groups, filters or ())
            logger.info("Loaded %s Telegram chat folders containing eligible groups/channels", folder_count)
        except Exception:
            logger.warning("Loading Telegram chat folders failed; continuing with full catalogue", exc_info=True)

        groups.sort(key=lambda x: x.title.casefold())
        logger.info("Loaded %s groups/channels", len(groups))
        return groups

    async def close(self) -> None:
        if not self.client.is_connected():
            return
        logger.info("Disconnecting Telegram client")
        result = self.client.disconnect()
        # Telethon's sync wrapper is dual-mode: while the event loop is running
        # it returns an awaitable, but during Qt/qasync shutdown it may complete
        # the disconnect synchronously and return None. Support both paths.
        if inspect.isawaitable(result):
            await result
        logger.info("Telegram client disconnected")
