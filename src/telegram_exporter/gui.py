from __future__ import annotations

from datetime import datetime, time, timezone
from pathlib import Path

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QInputDialog,
)
from qasync import asyncSlot

from .exporter import export_group
from .models import ExportMode, GroupExportPlan, GroupInfo
from .paths import credentials_path, session_path, settings_path, state_path
from .storage import LocalState, read_json, write_json_atomic
from .telegram_service import ApiCredentials, TelegramService

MODE_LABELS = {
    ExportMode.DATE_RANGE: "指定时间范围",
    ExportMode.UNREAD: "当前未读",
    ExportMode.SINCE_LAST_EXPORT: "上次导出以后",
}
MODE_BY_LABEL = {v: k for k, v in MODE_LABELS.items()}


class CredentialsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Telegram API 配置")
        self.resize(480, 190)
        layout = QFormLayout(self)
        self.api_id = QSpinBox()
        self.api_id.setMaximum(2_147_483_647)
        self.api_hash = QLineEdit()
        self.api_hash.setEchoMode(QLineEdit.Password)
        info = QLabel(
            '首次使用需要你自己的 Telegram API 凭据。请前往 '
            '<a href="https://my.telegram.org">my.telegram.org</a> → API Development Tools 获取。'
        )
        info.setOpenExternalLinks(True)
        info.setWordWrap(True)
        layout.addRow(info)
        layout.addRow("API ID", self.api_id)
        layout.addRow("API Hash", self.api_hash)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def value(self) -> ApiCredentials:
        return ApiCredentials(self.api_id.value(), self.api_hash.text().strip())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Telegram 多群批次导出器")
        self.resize(1220, 760)
        self.groups: list[GroupInfo] = []
        self.state = LocalState(state_path())
        self.service: TelegramService | None = None
        self._busy = False

        central = QWidget()
        root = QVBoxLayout(central)
        self.setCentralWidget(central)

        top = QHBoxLayout()
        self.connect_btn = QPushButton("连接 Telegram")
        self.refresh_btn = QPushButton("刷新群组")
        self.refresh_btn.setEnabled(False)
        self.output_btn = QPushButton("选择输出目录")
        self.output_label = QLabel(str(self._default_output_dir()))
        self.output_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        top.addWidget(self.connect_btn)
        top.addWidget(self.refresh_btn)
        top.addWidget(self.output_btn)
        top.addStretch(1)
        root.addLayout(top)
        root.addWidget(self.output_label)

        hint = QLabel(
            "一次可导出多个群；每个群可单独选择『指定时间范围 / 当前未读 / 上次导出以后』。"
            "每次导出都是独立批次，不会合并历史消息。"
        )
        hint.setWordWrap(True)
        root.addWidget(hint)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["导出", "群组", "导出方式", "开始日期", "结束日期", "未读", "状态"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        root.addWidget(self.table, 1)

        actions = QHBoxLayout()
        self.select_all_btn = QPushButton("全选")
        self.select_none_btn = QPushButton("全不选")
        self.bulk_10_btn = QPushButton("选中群设为最近 10 天")
        self.export_btn = QPushButton("开始导出")
        self.export_btn.setEnabled(False)
        actions.addWidget(self.select_all_btn)
        actions.addWidget(self.select_none_btn)
        actions.addWidget(self.bulk_10_btn)
        actions.addStretch(1)
        actions.addWidget(self.export_btn)
        root.addLayout(actions)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.status = QLabel("尚未连接 Telegram。")
        root.addWidget(self.progress)
        root.addWidget(self.status)

        self.connect_btn.clicked.connect(self.connect_telegram)
        self.refresh_btn.clicked.connect(self.refresh_groups)
        self.output_btn.clicked.connect(self.choose_output)
        self.select_all_btn.clicked.connect(lambda: self._set_all_checked(True))
        self.select_none_btn.clicked.connect(lambda: self._set_all_checked(False))
        self.bulk_10_btn.clicked.connect(self.bulk_recent_10)
        self.export_btn.clicked.connect(self.start_export)

    def _default_output_dir(self) -> Path:
        saved = read_json(settings_path(), {})
        return Path(saved.get("output_dir", str(Path.home() / "Documents" / "Telegram Exports")))

    def choose_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择导出目录", str(self._default_output_dir()))
        if path:
            self.output_label.setText(path)
            write_json_atomic(settings_path(), {"output_dir": path})

    def _load_credentials(self) -> ApiCredentials | None:
        payload = read_json(credentials_path(), None)
        if payload:
            return ApiCredentials(int(payload["api_id"]), payload["api_hash"])
        dlg = CredentialsDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return None
        creds = dlg.value()
        if not creds.api_id or not creds.api_hash:
            QMessageBox.warning(self, "配置无效", "API ID 和 API Hash 不能为空。")
            return None
        write_json_atomic(credentials_path(), {"api_id": creds.api_id, "api_hash": creds.api_hash})
        return creds

    async def _first_login(self) -> bool:
        assert self.service
        phone, ok = QInputDialog.getText(self, "Telegram 登录", "手机号（含国家区号，例如 +86...）：")
        if not ok or not phone.strip():
            return False
        self.status.setText("正在发送 Telegram 验证码…")
        await self.service.send_code(phone.strip())

        code, ok = QInputDialog.getText(self, "Telegram 验证码", "请输入 Telegram 收到的验证码：")
        if not ok or not code.strip():
            return False
        needs_password = not await self.service.sign_in_code(phone.strip(), code.strip())
        if needs_password:
            password, ok = QInputDialog.getText(
                self,
                "两步验证",
                "账号已启用两步验证，请输入 Telegram 2FA 密码：",
                QLineEdit.Password,
            )
            if not ok or not password:
                return False
            await self.service.sign_in_password(password)
        return True

    @asyncSlot()
    async def connect_telegram(self) -> None:
        if self._busy:
            return
        creds = self._load_credentials()
        if not creds:
            return
        self._set_busy(True, "正在连接 Telegram…")
        try:
            if self.service:
                await self.service.close()
            self.service = TelegramService(creds, session_path())
            authorized = await self.service.connect()
            if not authorized:
                authorized = await self._first_login()
            if not authorized:
                self.status.setText("登录已取消。")
                return
            self.refresh_btn.setEnabled(True)
            self.export_btn.setEnabled(True)
            self.connect_btn.setText("Telegram 已连接")
            await self._refresh_groups_impl()
        except Exception as exc:
            self._show_error(exc)
        finally:
            self._set_busy(False)

    @asyncSlot()
    async def refresh_groups(self) -> None:
        if self._busy or not self.service:
            return
        self._set_busy(True, "正在刷新群组…")
        try:
            await self._refresh_groups_impl()
        except Exception as exc:
            self._show_error(exc)
        finally:
            self._set_busy(False)

    async def _refresh_groups_impl(self) -> None:
        assert self.service
        groups = await self.service.list_groups()
        self._groups_loaded(groups)

    def _groups_loaded(self, groups: list[GroupInfo]) -> None:
        self.groups = groups
        self.table.setRowCount(len(groups))
        today = QDate.currentDate()
        for row, group in enumerate(groups):
            check = QCheckBox()
            check.setChecked(True)
            self.table.setCellWidget(row, 0, check)
            title = QTableWidgetItem(group.title)
            title.setToolTip(f"Telegram peer id: {group.chat_id}")
            self.table.setItem(row, 1, title)

            mode = QComboBox()
            for export_mode, label in MODE_LABELS.items():
                mode.addItem(label, export_mode.value)
            self.table.setCellWidget(row, 2, mode)

            start = QDateEdit(today.addDays(-9))
            start.setCalendarPopup(True)
            start.setDisplayFormat("yyyy-MM-dd")
            end = QDateEdit(today)
            end.setCalendarPopup(True)
            end.setDisplayFormat("yyyy-MM-dd")
            self.table.setCellWidget(row, 3, start)
            self.table.setCellWidget(row, 4, end)
            self.table.setItem(row, 5, QTableWidgetItem(str(group.unread_count)))
            self.table.setItem(row, 6, QTableWidgetItem("待导出"))
            mode.currentTextChanged.connect(lambda _text, r=row: self._update_row_mode(r))
        self.status.setText(f"已加载 {len(groups)} 个群组/频道。")

    def _update_row_mode(self, row: int) -> None:
        mode = self.table.cellWidget(row, 2)
        start = self.table.cellWidget(row, 3)
        end = self.table.cellWidget(row, 4)
        assert isinstance(mode, QComboBox) and isinstance(start, QDateEdit) and isinstance(end, QDateEdit)
        enabled = ExportMode(mode.currentData()) is ExportMode.DATE_RANGE
        start.setEnabled(enabled)
        end.setEnabled(enabled)
        status_item = self.table.item(row, 6)
        if status_item:
            if ExportMode(mode.currentData()) is ExportMode.UNREAD:
                status_item.setText("将按当前未读位置导出")
            elif ExportMode(mode.currentData()) is ExportMode.SINCE_LAST_EXPORT:
                last_id = self.state.last_message_id(self.groups[row].chat_id)
                status_item.setText(f"上次位置：{last_id}" if last_id else "尚无上次导出记录")
            else:
                status_item.setText("待导出")

    def _set_all_checked(self, checked: bool) -> None:
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 0)
            if isinstance(widget, QCheckBox):
                widget.setChecked(checked)

    def bulk_recent_10(self) -> None:
        today = QDate.currentDate()
        for row in range(self.table.rowCount()):
            check = self.table.cellWidget(row, 0)
            if not isinstance(check, QCheckBox) or not check.isChecked():
                continue
            mode = self.table.cellWidget(row, 2)
            start = self.table.cellWidget(row, 3)
            end = self.table.cellWidget(row, 4)
            assert isinstance(mode, QComboBox) and isinstance(start, QDateEdit) and isinstance(end, QDateEdit)
            mode.setCurrentIndex(mode.findData(ExportMode.DATE_RANGE.value))
            start.setDate(today.addDays(-9))
            end.setDate(today)

    def _plans(self) -> list[tuple[int, GroupExportPlan]]:
        plans: list[tuple[int, GroupExportPlan]] = []
        local_tz = datetime.now().astimezone().tzinfo or timezone.utc
        for row, group in enumerate(self.groups):
            check = self.table.cellWidget(row, 0)
            if not isinstance(check, QCheckBox) or not check.isChecked():
                continue
            mode_box = self.table.cellWidget(row, 2)
            start_edit = self.table.cellWidget(row, 3)
            end_edit = self.table.cellWidget(row, 4)
            assert isinstance(mode_box, QComboBox)
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
            plans.append((row, plan))
        return plans

    @asyncSlot()
    async def start_export(self) -> None:
        if self._busy or not self.service:
            return
        try:
            plans = self._plans()
        except ValueError as exc:
            QMessageBox.warning(self, "导出配置无效", str(exc))
            return
        if not plans:
            QMessageBox.information(self, "没有选择群组", "请至少选择一个群组。")
            return

        batch_name = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        batch_dir = Path(self.output_label.text()) / batch_name
        self._set_busy(True, f"准备导出 {len(plans)} 个群组…")
        self.progress.setRange(0, len(plans))
        self.progress.setValue(0)
        results = []
        failures: list[tuple[str, str]] = []
        try:
            for done, (row, plan) in enumerate(plans, start=1):
                status_item = self.table.item(row, 6)
                if status_item:
                    status_item.setText("导出中…")
                try:
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
                except Exception as exc:
                    failures.append((plan.group.title, f"{type(exc).__name__}: {exc}"))
                    if status_item:
                        status_item.setText("失败")
                self.progress.setValue(done)
                self.status.setText(f"进度：{done}/{len(plans)} 个群组")
        finally:
            self._set_busy(False)

        total = sum(r.message_count for r in results)
        if failures:
            detail = "\n".join(f"• {name}: {err}" for name, err in failures[:8])
            QMessageBox.warning(
                self,
                "导出部分完成",
                f"成功 {len(results)} 个群，共 {total} 条；失败 {len(failures)} 个。\n\n{detail}",
            )
        else:
            QMessageBox.information(
                self,
                "导出完成",
                f"成功导出 {len(results)} 个群组，共 {total} 条纯文本消息。\n\n输出目录：\n{batch_dir}",
            )
        self.status.setText(f"本批次完成：成功 {len(results)}，失败 {len(failures)}，共 {total} 条文本。")

    def _set_busy(self, busy: bool, status: str | None = None) -> None:
        self._busy = busy
        self.connect_btn.setEnabled(not busy)
        self.refresh_btn.setEnabled(not busy and self.service is not None)
        self.output_btn.setEnabled(not busy)
        self.export_btn.setEnabled(not busy and self.service is not None and bool(self.groups))
        if status:
            self.status.setText(status)

    def _show_error(self, exc: Exception) -> None:
        self.status.setText("操作失败。")
        QMessageBox.critical(self, "错误", f"{type(exc).__name__}: {exc}")

    async def shutdown(self) -> None:
        if self.service:
            await self.service.close()
