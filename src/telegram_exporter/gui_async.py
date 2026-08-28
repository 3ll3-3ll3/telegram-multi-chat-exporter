from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import QDialog, QInputDialog, QLineEdit, QMessageBox
from qasync import asyncSlot

from .diagnostics import friendly_error_message
from .exporter import export_group
from .gui import CredentialsDialog, MainWindow as BaseMainWindow
from .logging_setup import log_file_path
from .paths import credentials_path, session_files, session_path
from .storage import write_json_atomic
from .telegram_service import ApiCredentials, TelegramService

logger = logging.getLogger("telegram_exporter.gui")


class MainWindow(BaseMainWindow):
    """qasync-safe GUI.

    Qt's blocking ``exec()``/static convenience dialogs start a nested Qt event
    loop.  That is unsafe while a qasync coroutine is already executing and
    Telethon background tasks become ready.  This subclass keeps dialogs
    non-blocking and awaits their ``finished`` signal on the existing asyncio
    event loop instead.
    """

    def __init__(self):
        super().__init__()
        self._open_message_boxes: set[QMessageBox] = set()

    async def _await_dialog(self, dialog: QDialog) -> int:
        loop = asyncio.get_running_loop()
        future: asyncio.Future[int] = loop.create_future()

        def on_finished(result: int) -> None:
            if not future.done():
                future.set_result(result)

        dialog.finished.connect(on_finished)
        dialog.open()  # returns immediately; no nested Qt event loop
        try:
            return await future
        finally:
            try:
                dialog.finished.disconnect(on_finished)
            except (RuntimeError, TypeError):
                pass

    async def _prompt_text(
        self,
        title: str,
        label: str,
        *,
        echo_mode: QLineEdit.EchoMode = QLineEdit.Normal,
    ) -> tuple[str, bool]:
        dialog = QInputDialog(self)
        dialog.setWindowTitle(title)
        dialog.setLabelText(label)
        dialog.setInputMode(QInputDialog.TextInput)
        dialog.setTextEchoMode(echo_mode)
        result = await self._await_dialog(dialog)
        text = dialog.textValue()
        dialog.deleteLater()
        return text, result == QDialog.Accepted

    async def _edit_credentials_dialog(self, initial: ApiCredentials | None) -> ApiCredentials | None:
        dialog = CredentialsDialog(self, initial)
        result = await self._await_dialog(dialog)
        if result != QDialog.Accepted:
            dialog.deleteLater()
            return None
        value = dialog.value()
        dialog.deleteLater()
        return value

    async def _ask_yes_no(self, title: str, text: str) -> bool:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle(title)
        box.setText(text)
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setDefaultButton(QMessageBox.No)
        await self._await_dialog(box)
        clicked = box.standardButton(box.clickedButton())
        box.deleteLater()
        return clicked == QMessageBox.Yes

    def _show_message(self, icon: QMessageBox.Icon, title: str, text: str) -> None:
        """Show a message box without blocking the qasync event loop."""
        box = QMessageBox(self)
        box.setIcon(icon)
        box.setWindowTitle(title)
        box.setText(text)
        box.setStandardButtons(QMessageBox.Ok)
        self._open_message_boxes.add(box)

        def cleanup(_result: int) -> None:
            self._open_message_boxes.discard(box)
            box.deleteLater()

        box.finished.connect(cleanup)
        box.open()

    def _save_credentials(self, creds: ApiCredentials) -> bool:
        if creds.api_id <= 0 or not creds.api_hash:
            self._show_message(QMessageBox.Warning, "配置无效", "API ID 和 API Hash 不能为空。")
            return False
        write_json_atomic(credentials_path(), {"api_id": creds.api_id, "api_hash": creds.api_hash})
        logger.info("Telegram API credentials saved locally (api_id=%s; api_hash not logged)", creds.api_id)
        return True

    async def _load_credentials_async(self) -> ApiCredentials | None:
        saved = self._saved_credentials()
        if saved:
            return saved
        creds = await self._edit_credentials_dialog(None)
        if creds is None:
            return None
        return creds if self._save_credentials(creds) else None

    @asyncSlot()
    async def edit_api_settings(self) -> None:
        if self._busy:
            return
        creds = await self._edit_credentials_dialog(self._saved_credentials())
        if creds is None or not self._save_credentials(creds):
            return
        if self.service:
            await self.service.close()
            self.service = None
        self._mark_disconnected(clear_groups=True)
        self.status.setText("API 设置已保存。请点击『连接 Telegram』重新连接。")

    @asyncSlot()
    async def reset_login(self) -> None:
        if self._busy:
            return
        confirmed = await self._ask_yes_no(
            "重置 Telegram 登录",
            "这会删除本机由本程序创建的 Telegram Session，并要求下次重新输入手机号/验证码。\n\n"
            "不会删除 API ID/API Hash，也不会影响 Telegram 官方客户端。确定继续吗？",
        )
        if not confirmed:
            return
        self._set_busy(True, "正在重置本地登录状态…")
        try:
            if self.service:
                await self.service.close()
                self.service = None
            removed = 0
            for path in session_files():
                try:
                    if path.exists():
                        path.unlink()
                        removed += 1
                except OSError as exc:
                    logger.error("Failed to remove session file %s: %s", path.name, exc)
                    raise
            logger.info("Telegram local session reset; removed_files=%s", removed)
            self._mark_disconnected(clear_groups=True)
            self._show_message(
                QMessageBox.Information,
                "重置完成",
                "本地 Telegram Session 已清除。下次连接会重新登录。",
            )
        except Exception as exc:
            self._show_error(exc)
        finally:
            self._set_busy(False)

    async def _first_login(self) -> bool:
        assert self.service
        phone, ok = await self._prompt_text(
            "Telegram 登录",
            "手机号（含国家区号，例如 +86...）：",
        )
        if not ok or not phone.strip():
            logger.info("First login cancelled before phone submission")
            return False

        self.status.setText("正在发送 Telegram 验证码…")
        await self.service.send_code(phone.strip())

        code, ok = await self._prompt_text(
            "Telegram 验证码",
            "请输入 Telegram 收到的验证码：",
        )
        if not ok or not code.strip():
            logger.info("First login cancelled before code submission")
            return False

        needs_password = not await self.service.sign_in_code(phone.strip(), code.strip())
        if needs_password:
            password, ok = await self._prompt_text(
                "两步验证",
                "账号已启用两步验证，请输入 Telegram 2FA 密码：",
                echo_mode=QLineEdit.Password,
            )
            if not ok or not password:
                logger.info("First login cancelled before 2FA submission")
                return False
            await self.service.sign_in_password(password)
        return True

    @asyncSlot()
    async def connect_telegram(self) -> None:
        if self._busy:
            return
        creds = await self._load_credentials_async()
        if not creds:
            return
        self._set_busy(True, "正在连接 Telegram…")
        logger.info("User started Telegram connection (api_id=%s)", creds.api_id)
        try:
            if self.service:
                await self.service.close()
            self.service = TelegramService(creds, session_path())
            authorized = await self.service.connect()
            if not authorized:
                self.status.setText("网络已连接，账号尚未登录，准备发送验证码…")
                authorized = await self._first_login()
            if not authorized:
                self.status.setText("登录已取消。")
                return
            self.refresh_btn.setEnabled(True)
            self.export_btn.setEnabled(True)
            self.connect_btn.setText("Telegram 已连接")
            await self._refresh_groups_impl()
            logger.info("Telegram connection and dialog loading succeeded")
        except Exception as exc:
            self._show_error(exc)
        finally:
            self._set_busy(False)

    @asyncSlot()
    async def start_export(self) -> None:
        if self._busy or not self.service:
            return
        try:
            plans = self._plans()
        except ValueError as exc:
            self._show_message(QMessageBox.Warning, "导出配置无效", str(exc))
            return
        if not plans:
            self._show_message(QMessageBox.Information, "没有选择群组", "请至少选择一个群组。")
            return

        batch_name = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        batch_dir = Path(self.output_label.text()) / batch_name
        self._set_busy(True, f"准备导出 {len(plans)} 个群组…")
        self.progress.setRange(0, len(plans))
        self.progress.setValue(0)
        results = []
        failures: list[tuple[str, str]] = []
        logger.info("Starting export batch %s with %s groups", batch_name, len(plans))
        try:
            for done, (row, plan) in enumerate(plans, start=1):
                status_item = self.table.item(row, 6)
                if status_item:
                    status_item.setText("导出中…")
                try:
                    logger.info("Exporting group '%s' mode=%s", plan.group.title, plan.mode.value)
                    result = await export_group(self.service.client, plan, batch_dir)
                    results.append(result)
                    if result.latest_message_id:
                        self.state.mark_success(
                            result.chat_id,
                            result.latest_message_id,
                            datetime.now().astimezone().isoformat(timespec="seconds"),
                        )
                    if status_item:
                        status_item.setText(f"完成：{result.message_count} 条")
                    logger.info("Exported group '%s': %s messages", plan.group.title, result.message_count)
                except Exception as exc:
                    logger.error(
                        "Export failed for group '%s'",
                        plan.group.title,
                        exc_info=(type(exc), exc, exc.__traceback__),
                    )
                    failures.append((plan.group.title, f"{type(exc).__name__}: {exc}"))
                    if status_item:
                        status_item.setText("失败")
                self.progress.setValue(done)
                self.status.setText(f"进度：{done}/{len(plans)} 个群组")
        finally:
            self._set_busy(False)

        total = sum(r.message_count for r in results)
        logger.info("Export batch completed: success=%s failed=%s messages=%s", len(results), len(failures), total)
        if failures:
            detail = "\n".join(f"• {name}: {err}" for name, err in failures[:8])
            self._show_message(
                QMessageBox.Warning,
                "导出部分完成",
                f"成功 {len(results)} 个群，共 {total} 条；失败 {len(failures)} 个。\n\n{detail}\n\n日志：{log_file_path()}",
            )
        else:
            self._show_message(
                QMessageBox.Information,
                "导出完成",
                f"成功导出 {len(results)} 个群组，共 {total} 条纯文本消息。\n\n输出目录：\n{batch_dir}",
            )
        self.status.setText(f"本批次完成：成功 {len(results)}，失败 {len(failures)}，共 {total} 条文本。")

    def _show_error(self, exc: Exception) -> None:
        logger.error("GUI operation failed", exc_info=(type(exc), exc, exc.__traceback__))
        friendly = friendly_error_message(exc)
        raw = f"{type(exc).__name__}: {exc}"
        self.status.setText("操作失败。可点击『打开日志目录』查看详细日志。")
        self._show_message(
            QMessageBox.Critical,
            "Telegram 操作失败",
            f"{friendly}\n\n原始错误：{raw}\n\n日志文件：\n{log_file_path()}",
        )
