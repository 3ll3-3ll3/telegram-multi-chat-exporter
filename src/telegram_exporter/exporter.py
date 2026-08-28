from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from telethon import TelegramClient
from telethon.tl.custom.message import Message

from .desktop_json import ExportMessage, build_chat_export
from .models import ExportMode, GroupExportPlan

ProgressCallback = Callable[[int, int | None], None]


@dataclass(slots=True)
class ExportResult:
    chat_id: int
    title: str
    message_count: int
    latest_message_id: int
    result_path: Path


def safe_folder_name(value: str) -> str:
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value).strip().rstrip(".")
    return value[:120] or "Telegram Chat"


async def _sender_fields(message: Message) -> tuple[str | None, str | None]:
    sender = await message.get_sender()
    if sender is None:
        return None, None
    name = " ".join(
        p for p in [getattr(sender, "first_name", None), getattr(sender, "last_name", None)] if p
    ).strip()
    if not name:
        name = getattr(sender, "title", None) or getattr(sender, "username", None)
    sender_id = getattr(sender, "id", None)
    kind = "user" if getattr(sender, "first_name", None) is not None else "channel"
    return name or None, f"{kind}{sender_id}" if sender_id is not None else None


def _message_text(message: Message) -> str:
    # Telethon .message includes normal text and media caption text.
    return (message.message or "").strip()


async def export_group(
    client: TelegramClient,
    plan: GroupExportPlan,
    batch_dir: Path,
    progress: ProgressCallback | None = None,
) -> ExportResult:
    plan.validate()
    entity = await client.get_entity(plan.group.chat_id)

    kwargs: dict = {"reverse": True}
    if plan.mode is ExportMode.DATE_RANGE:
        kwargs["offset_date"] = plan.start_at
    elif plan.mode is ExportMode.UNREAD:
        kwargs["min_id"] = plan.group.read_inbox_max_id
    elif plan.mode is ExportMode.SINCE_LAST_EXPORT:
        kwargs["min_id"] = plan.last_export_message_id

    exported: list[ExportMessage] = []
    latest_id = 0

    # A dialog with zero unread messages should produce a valid empty batch file,
    # not accidentally fall back to min_id=0 and walk the whole chat history.
    should_fetch = not (plan.mode is ExportMode.UNREAD and plan.group.unread_count <= 0)

    if should_fetch:
        async for message in client.iter_messages(entity, **kwargs):
            if not isinstance(message, Message):
                continue

            # DATE_RANGE uses inclusive application-level boundary checks.
            if plan.mode is ExportMode.DATE_RANGE:
                if plan.start_at and message.date < plan.start_at:
                    continue
                if plan.end_at and message.date > plan.end_at:
                    break

            latest_id = max(latest_id, int(message.id))
            text = _message_text(message)
            if not text:
                continue

            from_name, from_id = await _sender_fields(message)
            reply_to = None
            if message.reply_to is not None:
                reply_to = getattr(message.reply_to, "reply_to_msg_id", None)

            exported.append(
                ExportMessage(
                    id=int(message.id),
                    date=message.date,
                    from_name=from_name,
                    from_id=from_id,
                    text=text,
                    reply_to_message_id=reply_to,
                    edited=message.edit_date,
                )
            )
            if progress and len(exported) % 100 == 0:
                progress(len(exported), None)

    folder = batch_dir / safe_folder_name(plan.group.title)
    folder.mkdir(parents=True, exist_ok=True)
    result_path = folder / "result.json"
    payload = build_chat_export(
        name=plan.group.title,
        chat_id=plan.group.chat_id,
        chat_type="private_supergroup",
        messages=exported,
    )
    with result_path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
        f.write("\n")

    if progress:
        progress(len(exported), len(exported))
    return ExportResult(
        chat_id=plan.group.chat_id,
        title=plan.group.title,
        message_count=len(exported),
        latest_message_id=latest_id,
        result_path=result_path,
    )
