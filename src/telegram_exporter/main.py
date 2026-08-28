from __future__ import annotations

import asyncio
import sys

from PySide6.QtWidgets import QApplication
from qasync import QEventLoop

from .gui import MainWindow


async def _run_app(app: QApplication) -> int:
    close_event = asyncio.Event()
    app.aboutToQuit.connect(close_event.set)
    window = MainWindow()
    window.show()
    await close_event.wait()
    await window.shutdown()
    return 0


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("Telegram Multi-Chat Exporter")
    app.setOrganizationName("WJL")
    return asyncio.run(_run_app(app), loop_factory=QEventLoop)


if __name__ == "__main__":
    raise SystemExit(main())
