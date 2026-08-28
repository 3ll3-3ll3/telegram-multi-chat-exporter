from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from .models import GroupInfo


class GroupSelectorDialog(QDialog):
    """Searchable selector for the full Telegram dialog catalogue.

    The main window should only display the selected working set. This dialog
    may contain hundreds or thousands of groups/channels without making the
    export editor itself noisy.
    """

    def __init__(self, groups: list[GroupInfo], selected_ids: set[int], parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择要放到编辑面板的群组")
        self.resize(720, 680)
        self._groups = groups

        root = QVBoxLayout(self)
        intro = QLabel(
            "这里是账号中的完整群组/频道目录。搜索并勾选你常用的少量群组；"
            "只有勾中的项目会出现在主界面的导出编辑面板。"
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        self.search = QLineEdit()
        self.search.setPlaceholderText("搜索群名或 @username…")
        self.search.setClearButtonEnabled(True)
        root.addWidget(self.search)

        toolbar = QHBoxLayout()
        self.visible_all_btn = QPushButton("勾选当前搜索结果")
        self.visible_none_btn = QPushButton("取消当前搜索结果")
        self.count_label = QLabel()
        toolbar.addWidget(self.visible_all_btn)
        toolbar.addWidget(self.visible_none_btn)
        toolbar.addStretch(1)
        toolbar.addWidget(self.count_label)
        root.addLayout(toolbar)

        self.list = QListWidget()
        self.list.setAlternatingRowColors(True)
        root.addWidget(self.list, 1)

        for group in groups:
            suffix = f"  @{group.username}" if group.username else ""
            unread = f"  · 未读 {group.unread_count}" if group.unread_count else ""
            item = QListWidgetItem(f"{group.title}{suffix}{unread}")
            item.setData(Qt.ItemDataRole.UserRole, group.chat_id)
            item.setData(Qt.ItemDataRole.UserRole + 1, f"{group.title} {group.username or ''}".casefold())
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if group.chat_id in selected_ids else Qt.CheckState.Unchecked)
            self.list.addItem(item)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.search.textChanged.connect(self._apply_filter)
        self.visible_all_btn.clicked.connect(lambda: self._set_visible(Qt.CheckState.Checked))
        self.visible_none_btn.clicked.connect(lambda: self._set_visible(Qt.CheckState.Unchecked))
        self.list.itemChanged.connect(lambda _item: self._update_count())
        self._update_count()

    def _apply_filter(self, text: str) -> None:
        needle = text.strip().casefold()
        for row in range(self.list.count()):
            item = self.list.item(row)
            haystack = str(item.data(Qt.ItemDataRole.UserRole + 1) or "")
            item.setHidden(bool(needle and needle not in haystack))

    def _set_visible(self, state: Qt.CheckState) -> None:
        self.list.blockSignals(True)
        try:
            for row in range(self.list.count()):
                item = self.list.item(row)
                if not item.isHidden():
                    item.setCheckState(state)
        finally:
            self.list.blockSignals(False)
        self._update_count()

    def _update_count(self) -> None:
        selected = sum(
            1
            for row in range(self.list.count())
            if self.list.item(row).checkState() == Qt.CheckState.Checked
        )
        self.count_label.setText(f"已选 {selected} / {self.list.count()}")

    def selected_ids(self) -> set[int]:
        return {
            int(self.list.item(row).data(Qt.ItemDataRole.UserRole))
            for row in range(self.list.count())
            if self.list.item(row).checkState() == Qt.CheckState.Checked
        }
