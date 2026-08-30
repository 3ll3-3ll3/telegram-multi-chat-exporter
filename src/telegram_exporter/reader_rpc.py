from __future__ import annotations

from datetime import datetime
from typing import Any

from .bridge_errors import INVALID_ARGUMENT, TelegramBridgeError
from .reader_service import PersonalAccountReader

READER_METHODS = {
    "account.get",
    "dialogs.list",
    "chats.get",
    "chats.members",
    "messages.history",
}


def _parse_iso(value: Any) -> datetime | None:
    if value in {None, ""}:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError as exc:
        raise TelegramBridgeError(INVALID_ARGUMENT, f"无法解析时间：{value}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return parsed


async def _reader(server: Any) -> PersonalAccountReader:
    service = await server._authorized_service()
    current = getattr(server, "_v3_reader", None)
    if current is None or current.telegram_service is not service:
        current = PersonalAccountReader(service)
        server._v3_reader = current
    return current


async def dispatch_reader(server: Any, method: str, params: dict[str, Any]) -> Any:
    async def operation():
        reader = await _reader(server)
        if method == "account.get":
            return await reader.account_profile()
        if method == "dialogs.list":
            return await reader.dialogs_page(
                dialog_type=params.get("dialog_type"),
                folder=params.get("folder"),
                archived=str(params.get("archived") or "all"),
                search=params.get("search"),
                unread=str(params.get("unread") or "all"),
                pinned=str(params.get("pinned") or "all"),
                cursor=params.get("cursor"),
                limit=int(params.get("limit", 100)),
            )
        if method == "chats.get":
            return await reader.chat_details(params.get("chat", ""))
        if method == "chats.members":
            return await reader.members_page(
                params.get("chat", ""),
                role=params.get("role"),
                cursor=params.get("cursor"),
                limit=int(params.get("limit", 100)),
            )
        if method == "messages.history":
            return await reader.messages_history_page(
                params.get("chat", ""),
                cursor=params.get("cursor"),
                limit=int(params.get("limit", 100)),
                since=_parse_iso(params.get("since")),
                until=_parse_iso(params.get("until")),
            )
        if method == "messages.get" and params.get("schema") == "v3":
            return await reader.messages_get_v3(
                params.get("chat", ""),
                [int(value) for value in params.get("ids", [])],
            )
        raise TelegramBridgeError(INVALID_ARGUMENT, f"未知 reader method：{method}")

    return await server.operations.run_read(operation)
