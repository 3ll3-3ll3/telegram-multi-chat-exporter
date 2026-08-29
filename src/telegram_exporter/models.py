from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ExportMode(StrEnum):
    DATE_RANGE = "date_range"
    UNREAD = "unread"
    SINCE_LAST_EXPORT = "since_last_export"


@dataclass(frozen=True, slots=True)
class FolderRef:
    """A Telegram account chat-folder reference attached to an eligible group."""

    folder_id: int
    title: str
    order: int = 0


@dataclass(slots=True)
class GroupInfo:
    chat_id: int
    title: str
    username: str | None = None
    unread_count: int = 0
    read_inbox_max_id: int = 0
    latest_message_id: int = 0
    # Whether Telegram exposes a profile photo for this chat. The selector may
    # lazily fetch the small avatar into a local UI cache; export semantics stay
    # text-only and result.json never includes the avatar.
    has_photo: bool = False
    # Traits below are used only to evaluate Telegram account-side chat folders.
    is_group: bool = False
    is_broadcast: bool = False
    is_muted: bool = False
    is_archived: bool = False
    is_unread: bool = False
    folders: tuple[FolderRef, ...] = ()


@dataclass(slots=True)
class GroupExportPlan:
    group: GroupInfo
    mode: ExportMode
    start_at: datetime | None = None
    end_at: datetime | None = None
    last_export_message_id: int = 0

    def validate(self) -> None:
        if self.mode is ExportMode.DATE_RANGE:
            if self.start_at is None or self.end_at is None:
                raise ValueError("时间范围模式必须同时指定开始和结束时间。")
            if self.start_at > self.end_at:
                raise ValueError("开始时间不能晚于结束时间。")
        elif self.mode is ExportMode.SINCE_LAST_EXPORT and self.last_export_message_id <= 0:
            raise ValueError(
                f"群组「{self.group.title}」还没有上次成功导出记录。"
                "请先使用指定时间范围或当前未读模式完成一次导出。"
            )
