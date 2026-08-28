from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ExportMode(StrEnum):
    DATE_RANGE = "date_range"
    UNREAD = "unread"
    SINCE_LAST_EXPORT = "since_last_export"


@dataclass(slots=True)
class GroupInfo:
    chat_id: int
    title: str
    username: str | None = None
    unread_count: int = 0
    read_inbox_max_id: int = 0
    latest_message_id: int = 0


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
