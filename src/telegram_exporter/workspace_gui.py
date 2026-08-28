from __future__ import annotations

import asyncio
import logging
from datetime import datetime, time, timezone
from pathlib import Path

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QHeaderView,
    QMessageBox,
    QTableWidgetItem,
)
from qasync import asyncSlot

from .diagnostics import friendly_error_message
from .exporter import export_group
from .group_selector import GroupSelectorDialog
from .gui import CredentialsDialog, MainWindow as BaseMainWindow, MODE_LABELS
from .logging_setup import log_file_path
from .models import ExportMode, GroupExportPlan, GroupInfo
from .paths import session_files
from .read_state import mark_unread_snapshot_read

logger = logging.getLogger("telegram_exporter.workspace_gui")

RowSettings = tuple[bool, str, QDate, QDate, bool]


class MainWindow(BaseMainWindow):
    """Focused workspace UI with an explicit, default-off read-state policy."""

    def __init__(self):
        super().__init__()
        self._transient_dialogs: list[QDialog] = []
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(
            ["导出", "群组", "导出方式", "开始日期", "结束日期", "未读", "导出后标已读", "状态"]
        )
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeToContents)

    def _keep_dialog(self, dialog: QDialog) -> None:
        self._transient_dialogs.append(dialog)

        def cleanup(_result: int) -> None:
            try:
                self._transient_dialogs.remove(dialog)
            except ValueError:
                pass

        dialog.finished.connect(cleanup)

    async def _await_dialog(self, dialog: QDialog) -> int:
        loop = asyncio.get_running_loop()
        future: asyncio.Future[int] = loop.create_future()
        self._keep_dialog(dialog)

        def finished(result: int) -> None:
            if not future.done():
                future.set_result(result)

        dialog.finished.connect(finished)
        dialog.open()
        return await future

    def _notify(self, icon: QMessageBox.Icon, title: str, text: str) -> None:
        box = QMessageBox(self)
        box.setIcon(icon)
        box.setWindowTitle(title)
        box.setText(text)
        box.setStandardButtons(QMessageBox.StandardButton.Ok)
        self._keep_dialog(box)
        box.open()

    def choose_output(self) -> None:
        dialog = QFileDialog(self, "选择导出目录", str(self._default_output_dir()))
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)

        def selected(path: str) -> None:
            if path:
                self.output_label.setText(path)
                self._update_settings(output_dir=path)
                logger.info("Output directory changed to %s", path)

        dialog.fileSelected.connect(selected)
        self._keep_dialog(dialog)
        dialog.open()

    def select_groups(self) -> None:
        if not self.all_groups:
            self._notify(QMessageBox.Icon.Information, "群组目录为空", "请先连接 Telegram 并加载群组目录。")
            return

        previous = self._capture_row_settings()
        dialog = GroupSelectorDialog(self.all_groups, self._selected_group_ids(), self)

        def finished(result: int) -> None:
            if result != QDialog.Accepted:
                return
            selected_ids = dialog.selected_ids()
            self._update_settings(selected_group_ids=sorted(selected_ids))
            selected = [g for g in self.all_groups if g.chat_id in selected_ids]
            self._render_groups(selected, previous)
            logger.info(
                "Workspace group selection updated: selected=%s catalog=%s",
                len(selected),
                len(self.all_groups),
            )
            if selected:
                self.status.setText(f"群组目录共 {len(self.all_groups)} 个；编辑面板只显示已选 {len(selected)} 个。")
            else:
                self.status.setText(f"群组目录共 {len(self.all_groups)} 个；当前未选择工作群。")

        dialog.finished.connect(finished)
        self._keep_dialog(dialog)
        dialog.open()

    @asyncSlot()
    async def edit_api_settings(self) -> None:
        if self._busy:
            return
        current = self._saved_credentials()
        dialog = CredentialsDialog(self, current)
        if await self._await_dialog(dialog) != QDialog.Accepted:
            return
        creds = dialog.value()
        if not self._save_credentials(creds):
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

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Question)
        box.setWindowTitle("重置 Telegram 登录")
        box.setText(
            "这会删除本机由本程序创建的 Telegram Session，并要求下次重新输入手机号/验证码。\n\n"
            "不会删除 API ID/API Hash，也不会影响 Telegram 官方客户端。确定继续吗？"
        )
        box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        box.setDefaultButton(QMessageBox.StandardButton.No)
        await self._await_dialog(box)
        if box.standardButton(box.clickedButton()) != QMessageBox.StandardButton.Yes:
            return

        self._set_busy(True, "正在重置本地登录状态…")
        try:
            if self.service:
                await self.service.close()
                self.service = None
            removed = 0
            for path in session_files():
                if path.exists():
                    path.unlink()
                    removed += 1
            logger.info("Telegram local session reset; removed_files=%s", removed)
            self._mark_disconnected(clear_groups=True)
            self._notify(QMessageBox.Icon.Information, "重置完成", "本地 Telegram Session 已清除。下次连接会重新登录。")
        except Exception as exc:
            self._show_error(exc)
        finally:
            self._set_busy(False)

    def _mark_read_preferences(self) -> dict[str, bool]:
        raw = self._settings().get("mark_read_after_export", {})
        if not isinstance(raw, dict):
            return {}
        return {str(key): bool(value) for key, value in raw.items()}

    def _saved_mark_read(self, chat_id: int) -> bool:
        return self._mark_read_preferences().get(str(chat_id), False)

    def _save_mark_read(self, chat_id: int, checked: bool) -> None:
        preferences = self._mark_read_preferences()
        if checked:
            preferences[str(chat_id)] = True
        else:
            preferences.pop(str(chat_id), None)
        self._update_settings(mark_read_after_export=preferences)

    def _mark_read_changed(self, chat_id: int, row: int, checked: bool) -> None:
        self._save_mark_read(chat_id, checked)
        self._update_row_mode(row)

    def _capture_row_settings(self) -> dict[int, RowSettings]:
        result: dict[int, RowSettings] = {}
        for row, group in enumerate(self.groups):
            check = self.table.cellWidget(row, 0)
            mode = self.table.cellWidget(row, 2)
            start = self.table.cellWidget(row, 3)
            end = self.table.cellWidget(row, 4)
            mark_read = self.table.cellWidget(row, 6)
            if not (
                isinstance(check, QCheckBox)
                and isinstance(mode, QComboBox)
                and isinstance(start, QDateEdit)
                and isinstance(end, QDateEdit)
                and isinstance(mark_read, QCheckBox)
            ):
                continue
            result[group.chat_id] = (
                check.isChecked(),
                str(mode.currentData()),
                start.date(),
                end.date(),
                mark_read.isChecked(),
            )
        return result

    def _render_groups(
        self,
        groups: list[GroupInfo],
        previous: dict[int, RowSettings] | None = None,
    ) -> None:
        self.groups = groups
        self.table.setRowCount(len(groups))
        today = QDate.currentDate()
        previous = previous or {}

        for row, group in enumerate(groups):
            saved = previous.get(group.chat_id)

            check = QCheckBox()
            check.setChecked(saved[0] if saved else True)
            self.table.setCellWidget(row, 0, check)

            title = QTableWidgetItem(group.title)
            title.setToolTip(f"Telegram peer id: {group.chat_id}")
            self.table.setItem(row, 1, title)

            mode = QComboBox()
            for export_mode, label in MODE_LABELS.items():
                mode.addItem(label, export_mode.value)
            if saved:
                index = mode.findData(saved[1])
                if index >= 0:
                    mode.setCurrentIndex(index)
            self.table.setCellWidget(row, 2, mode)

            start = QDateEdit(saved[2] if saved else today.addDays(-9))
            start.setCalendarPopup(True)
            start.setDisplayFormat("yyyy-MM-dd")
            end = QDateEdit(saved[3] if saved else today)
            end.setCalendarPopup(True)
            end.setDisplayFormat("yyyy-MM-dd")
            self.table.setCellWidget(row, 3, start)
            self.table.setCellWidget(row, 4, end)

            unread_item = QTableWidgetItem(str(group.unread_count))
            self.table.setItem(row, 5, unread_item)

            mark_read = QCheckBox()
            mark_read.setChecked(saved[4] if saved else self._saved_mark_read(group.chat_id))
            mark_read.setToolTip(
                "仅『当前未读』模式可用。勾选后，只有 JSON 成功写入后才会把本次刷新快照标记为已读。\n"
                "Telegram 的已读游标按消息 ID 推进，因此快照内图片、文件、系统消息等非文本项也会一起变成已读。"
            )
            self.table.setCellWidget(row, 6, mark_read)
            self.table.setItem(row, 7, QTableWidgetItem("待导出"))

            mode.currentTextChanged.connect(lambda _text, r=row: self._update_row_mode(r))
            mark_read.toggled.connect(
                lambda checked, gid=group.chat_id, r=row: self._mark_read_changed(gid, r, checked)
            )
            self._update_row_mode(row)

        self.export_btn.setEnabled(bool(groups) and self.service is not None and not self._busy)

    def _update_row_mode(self, row: int) -> None:
        mode = self.table.cellWidget(row, 2)
        start = self.table.cellWidget(row, 3)
        end = self.table.cellWidget(row, 4)
        mark_read = self.table.cellWidget(row, 6)
        assert (
            isinstance(mode, QComboBox)
            and isinstance(start, QDateEdit)
            and isinstance(end, QDateEdit)
            and isinstance(mark_read, QCheckBox)
        )

        export_mode = ExportMode(mode.currentData())
        is_range = export_mode is ExportMode.DATE_RANGE
        is_unread = export_mode is ExportMode.UNREAD
        start.setEnabled(is_range)
        end.setEnabled(is_range)
        mark_read.setEnabled(is_unread)

        status_item = self.table.item(row, 7)
        if not status_item:
            return
        if is_unread:
            if mark_read.isChecked():
                status_item.setText("导出成功后标已读（快照内非文本项也会一起已读）")
            else:
                status_item.setText("只读导出：不会改变 Telegram 已读状态")
        elif export_mode is ExportMode.SINCE_LAST_EXPORT:
            last_id = self.state.last_message_id(self.groups[row].chat_id)
            status_item.setText(f"上次位置：{last_id}" if last_id else "尚无上次导出记录")
        else:
            status_item.setText("待导出")

    def _plans(self) -> list[tuple[int, GroupExportPlan, bool]]:
        plans: list[tuple[int, GroupExportPlan, bool]] = []
        local_tz = datetime.now().astimezone().tzinfo or timezone.utc

        for row, group in enumerate(self.groups):
            check = self.table.cellWidget(row, 0)
            if not isinstance(check, QCheckBox) or not check.isChecked():
                continue

            mode_box = self.table.cellWidget(row, 2)
            start_edit = self.table.cellWidget(row, 3)
            end_edit = self.table.cellWidget(row, 4)
            mark_read_box = self.table.cellWidget(row, 6)
            assert isinstance(mode_box, QComboBox) and isinstance(mark_read_box, QCheckBox)

            mode = ExportMode(mode_box.currentData())
            start_at = end_at = None
            if mode is ExportMode.DATE_RANGE:
                assert isinstance(start_edit, QDateEdit) and isinstance(end_edit, QDateEdit)
                start_at = datetime.combine(start_edit.date().toPython(), time.min, local_tz)
                end_at = datetime.combine(end_edit.date().toPython(), time.max, local_tz)

            plan = GroupExportPlan(
                group=group,
                mode=mode,
                start_at=start_at,
                end_at=end_at,
                last_export_message_id=self.state.last_message_id(group.chat_id),
            )
            plan.validate()
            plans.append((row, plan, mode is ExportMode.UNREAD and mark_read_box.isChecked()))

        return plans

    @asyncSlot()
    async def start_export(self) -> None:
        if self._busy or not self.service:
            return
        try:
            plans = self._plans()
        except ValueError as exc:
            self._notify(QMessageBox.Icon.Warning, "导出配置无效", str(exc))
            return
        if not plans:
            self._notify(QMessageBox.Icon.Information, "没有选择群组", "请至少选择一个群组。")
            return

        batch_name = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        batch_dir = Path(self.output_label.text()) / batch_name
        self._set_busy(True, f"准备导出 {len(plans)} 个群组…")
        self.progress.setRange(0, len(plans))
        self.progress.setValue(0)
        results = []
        failures: list[tuple[str, str]] = []
        read_failures: list[tuple[str, str]] = []
        marked_read_count = 0
        logger.info("Starting export batch %s with %s groups", batch_name, len(plans))

        try:
            for done, (row, plan, mark_read_after_export) in enumerate(plans, start=1):
                status_item = self.table.item(row, 7)
                if status_item:
                    status_item.setText("导出中…")
                try:
                    logger.info(
                        "Exporting group '%s' mode=%s mark_read_after_export=%s",
                        plan.group.title,
                        plan.mode.value,
                        mark_read_after_export,
                    )
                    result = await export_group(self.service.client, plan, batch_dir)
                    results.append(result)

                    if result.latest_message_id:
                        self.state.mark_success(
                            result.chat_id,
                            result.latest_message_id,
                            datetime.now().astimezone().isoformat(timespec="seconds"),
                        )

                    suffix = ""
                    if mark_read_after_export:
                        try:
                            acknowledged_id = await mark_unread_snapshot_read(self.service.client, plan.group)
                            if acknowledged_id is not None:
                                marked_read_count += 1
                                plan.group.read_inbox_max_id = acknowledged_id
                                plan.group.unread_count = 0
                                unread_item = self.table.item(row, 5)
                                if unread_item:
                                    unread_item.setText("0")
                                    unread_item.setToolTip("已处理刷新时的未读快照；请刷新群组目录获取之后到达的新消息。")
                                suffix = "；已标已读"
                            else:
                                suffix = "；无未读需标记"
                        except Exception as read_exc:
                            logger.error(
                                "Read acknowledgement failed for group '%s' after successful export",
                                plan.group.title,
                                exc_info=(type(read_exc), read_exc, read_exc.__traceback__),
                            )
                            read_failures.append((plan.group.title, f"{type(read_exc).__name__}: {read_exc}"))
                            suffix = "；标已读失败"

                    if status_item:
                        status_item.setText(f"完成：{result.message_count} 条{suffix}")
                    logger.info("Exported group '%s': %s messages", plan.group.title, result.message_count)
                except Exception as exc:
                    logger.error(
                        "Export failed for group '%s'",
                        plan.group.title,
                        exc_info=(type(exc), exc, exc.__traceback__),
                    )
                    failures.append((plan.group.title, f"{type(exc).__name__}: {exc}"))
                    if status_item:
                        status_item.setText("失败；未改变已读状态")

                self.progress.setValue(done)
                self.status.setText(f"进度：{done}/{len(plans)} 个群组")
        finally:
            self._set_busy(False)

        total = sum(result.message_count for result in results)
        logger.info(
            "Export batch completed: success=%s failed=%s messages=%s marked_read=%s read_failures=%s",
            len(results),
            len(failures),
            total,
            marked_read_count,
            len(read_failures),
        )

        if failures or read_failures:
            parts = [f"成功导出 {len(results)} 个群，共 {total} 条；导出失败 {len(failures)} 个。"]
            if marked_read_count:
                parts.append(f"其中 {marked_read_count} 个群已按你的设置同步标记已读。")
            if read_failures:
                parts.append(f"另有 {len(read_failures)} 个群 JSON 已成功，但『标已读』同步失败；文件仍然保留。")
            details = []
            details.extend(f"• 导出失败｜{name}: {err}" for name, err in failures[:6])
            details.extend(f"• 标已读失败｜{name}: {err}" for name, err in read_failures[:6])
            if details:
                parts.append("\n".join(details))
            parts.append(f"日志：{log_file_path()}")
            self._notify(QMessageBox.Icon.Warning, "本批次完成（有需要注意的项目）", "\n\n".join(parts))
        else:
            extra = f"\n其中 {marked_read_count} 个群已按设置标记为已读。" if marked_read_count else ""
            self._notify(
                QMessageBox.Icon.Information,
                "导出完成",
                f"成功导出 {len(results)} 个群组，共 {total} 条纯文本消息。{extra}\n\n输出目录：\n{batch_dir}",
            )

        self.status.setText(
            f"本批次完成：成功 {len(results)}，失败 {len(failures)}，共 {total} 条文本；已标已读 {marked_read_count} 个群。"
        )

    def _show_error(self, exc: Exception) -> None:
        logger.error("GUI operation failed", exc_info=(type(exc), exc, exc.__traceback__))
        friendly = friendly_error_message(exc)
        raw = f"{type(exc).__name__}: {exc}"
        self.status.setText("操作失败。可点击『打开日志目录』查看详细日志。")
        self._notify(
            QMessageBox.Icon.Critical,
            "Telegram 操作失败",
            f"{friendly}\n\n原始错误：{raw}\n\n日志文件：\n{log_file_path()}",
        )
