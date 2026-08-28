from __future__ import annotations

import asyncio
import logging
import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication
from qasync import QEventLoop

from .focused_gui import MainWindow
from .logging_setup import setup_logging

APP_STYLE = """
QWidget {
    font-size: 14px;
    color: #1f2937;
}
QMainWindow, QDialog {
    background: #f7f8fa;
}
QPushButton {
    min-height: 34px;
    padding: 0 14px;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    background: #ffffff;
}
QPushButton:hover {
    background: #f3f4f6;
    border-color: #9ca3af;
}
QPushButton:disabled {
    color: #9ca3af;
    background: #f3f4f6;
}
QPushButton[text="开始导出"] {
    background: #2563eb;
    color: white;
    border-color: #2563eb;
    font-weight: 600;
    min-width: 110px;
}
QLineEdit, QSpinBox, QComboBox, QDateEdit {
    min-height: 32px;
    padding: 0 8px;
    border: 1px solid #d1d5db;
    border-radius: 7px;
    background: #ffffff;
}
QTableWidget {
    background: #ffffff;
    alternate-background-color: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 10px;
    gridline-color: #eef0f3;
    selection-background-color: #dbeafe;
    selection-color: #1f2937;
}
QHeaderView::section {
    background: #f3f4f6;
    color: #4b5563;
    padding: 9px 7px;
    border: 0;
    border-bottom: 1px solid #e5e7eb;
    font-weight: 600;
}
QProgressBar {
    min-height: 18px;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    background: #ffffff;
    text-align: center;
}
QProgressBar::chunk {
    background: #2563eb;
    border-radius: 7px;
}
"""


async def _run_app(app: QApplication) -> int:
    close_event = asyncio.Event()
    app.aboutToQuit.connect(close_event.set)
    window = MainWindow()
    window.setWindowTitle("TG 导出器")
    window.show()
    await close_event.wait()
    try:
        await window.shutdown()
    except Exception:
        # Closing the GUI should never surface a PyInstaller fatal-error dialog
        # merely because best-effort Telegram cleanup failed during Qt teardown.
        logging.getLogger("telegram_exporter").exception("Application shutdown cleanup failed")
    return 0


def main() -> int:
    logger = setup_logging()
    logger.info("Starting TG Exporter")
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("TG Exporter")
        app.setOrganizationName("WJL")
        app.setStyle("Fusion")
        app.setFont(QFont("Microsoft YaHei UI", 10))
        app.setStyleSheet(APP_STYLE)
        return asyncio.run(_run_app(app), loop_factory=QEventLoop)
    except Exception:
        logging.getLogger("telegram_exporter").exception("Fatal application error")
        raise


if __name__ == "__main__":
    raise SystemExit(main())
