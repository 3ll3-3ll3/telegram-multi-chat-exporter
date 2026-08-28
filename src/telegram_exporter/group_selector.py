from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
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

from .models import FolderRef, GroupInfo


class GroupSelectorDialog(QDialog):
    """Searchable selector for the full Telegram dialog catalogue.

    The main window should only display the selected working set. Telegram's
    account-side chat folders (dialog filters) can narrow the catalogue before
    the user searches/checks groups.
    """

    def __init__(self, groups: list[GroupInfo], selected_ids: set[int], parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择要放到编辑面板的群组")
        self.resize(760, 700)
        self._groups = groups

        root = QVBoxLayout(self)
        intro = QLabel(
            "这里是账号中的完整群组/频道目录。可以先按 Telegram 账号里已有的聊天分组筛选，"
            "再搜索并勾选常用群组；只有勾中的项目会出现在主界面的导出编辑面板。"
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        folder_row = QHBoxLayout()
        folder_row.addWidget(QLabel("Telegram 分组："))
        self.folder = QComboBox()
        self.folder.setMinimumWidth(260)
        self.folder.addItem("全部群组/频道", None)

        folder_map: dict[int, FolderRef] = {}
        folder_counts: dict[int, int] = {}
        for group in groups:
            for ref in group.folders:
                folder_map.setdefault(ref.folder_id, ref)
                folder_counts[ref.folder_id] = folder_counts.get(ref.folder_id, 0) + 1
        for ref in sorted(folder_map.values(), key=lambda item: (item.order, item.title.casefold())):
            self.folder.addItem(f"{ref.title}  ({folder_counts.get(ref.folder_id, 0)})", ref.folder_id)

        folder_row.addWidget(self.folder, 1)
        if not folder_map:
            no_folder = QLabel("未读取到包含群组/频道的账号分组")
            no_folder.setStyleSheet("color: #6b7280;")
            folder_row.addWidget(no_folder)
        root.addLayout(folder_row)

        self.search = QLineEdit()
        self.search.setPlaceholderText("在当前分组中搜索群名或 @username…")
        self.search.setClearButtonEnabled(True)
        root.addWidget(self.search)

        toolbar = QHBoxLayout()
        self.visible_all_btn = QPushButton("勾选当前筛选结果")
        self.visible_none_btn = QPushButton("取消当前筛选结果")
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
            item.setData(Qt.ItemDataRole.UserRole + 2, [ref.folder_id for ref in group.folders])
            if group.folders:
                item.setToolTip("Telegram 分组：" + "、".join(ref.title for ref in group.folders))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if group.chat_id in selected_ids else Qt.CheckState.Unchecked)
            self.list.addItem(item)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

        self.search.textChanged.connect(self._apply_filter)
        self.folder.currentIndexChanged.connect(self._apply_filter)
        self.visible_all_btn.clicked.connect(lambda: self._set_visible(Qt.CheckState.Checked))
        self.visible_none_btn.clicked.connect(lambda: self._set_visible(Qt.CheckState.Unchecked))
        self.list.itemChanged.connect(lambda _item: self._update_count())
        self._apply_filter()

    def _apply_filter(self, *_args) -> None:
        needle = self.search.text().strip().casefold()
        folder_id = self.folder.currentData()
        for row in range(self.list.count()):
            item = self.list.item(row)
            haystack = str(item.data(Qt.ItemDataRole.UserRole + 1) or "")
            folder_ids = item.data(Qt.ItemDataRole.UserRole + 2) or []
            matches_text = not needle or needle in haystack
            matches_folder = folder_id is None or int(folder_id) in {int(value) for value in folder_ids}
            item.setHidden(not (matches_text and matches_folder))
        self._update_count()

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
        visible = sum(1 for row in range(self.list.count()) if not self.list.item(row).isHidden())
        self.count_label.setText(f"已选 {selected} / {self.list.count()} · 当前显示 {visible}")

    def selected_ids(self) -> set[int]:
        return {
            int(self.list.item(row).data(Qt.ItemDataRole.UserRole))
            for row in range(self.list.count())
            if self.list.item(row).checkState() == Qt.CheckState.Checked
        }
