from __future__ import annotations

import os
from pathlib import Path


class SessionBusyError(RuntimeError):
    """Raised when another TG Exporter/tgctl process owns the shared session."""


class SessionLease:
    def __init__(self, session_base: Path):
        self.path = session_base.with_suffix(".session.lock")
        self._file = None

    def acquire(self) -> None:
        if self._file is not None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        file = self.path.open("a+b")
        try:
            file.seek(0, os.SEEK_END)
            if file.tell() == 0:
                file.write(b"0")
                file.flush()
            file.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, BlockingIOError) as exc:
            file.close()
            raise SessionBusyError(
                "Telegram Session 正在被另一个 TG Exporter/tgctl 进程使用。"
                "请关闭 TG Exporter GUI 或等待另一个 tgctl 命令结束后重试。"
            ) from exc
        self._file = file

    def release(self) -> None:
        file = self._file
        if file is None:
            return
        try:
            file.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(file.fileno(), fcntl.LOCK_UN)
        finally:
            file.close()
            self._file = None

    def __enter__(self) -> "SessionLease":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()
