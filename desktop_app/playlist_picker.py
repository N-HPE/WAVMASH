"""Searchable playlist picker widget for context menus."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class PlaylistPickerWidget(QWidget):
    """Compact playlist list with search and “new playlist” action."""

    playlist_chosen = Signal(str)
    new_playlist_requested = Signal()

    def __init__(self, playlist_names: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._all_names = sorted(playlist_names, key=str.casefold)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Find a playlist")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._apply_filter)
        root.addWidget(self.search)

        self.list_widget = QListWidget()
        self.list_widget.setMouseTracking(True)
        self.list_widget.setFrameShape(QListWidget.NoFrame)
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_widget.setMaximumHeight(220)
        self.list_widget.setMinimumWidth(220)
        for name in self._all_names:
            QListWidgetItem(name, self.list_widget)
        self.list_widget.itemClicked.connect(
            lambda item: self.playlist_chosen.emit(item.text())
        )
        self.search.returnPressed.connect(self._activate_first_visible)
        root.addWidget(self.list_widget)

        self.new_btn = QPushButton("  New playlist")
        self.new_btn.setCursor(Qt.PointingHandCursor)
        self.new_btn.setFlat(True)
        self.new_btn.clicked.connect(self.new_playlist_requested.emit)
        new_row = QHBoxLayout()
        new_row.setContentsMargins(4, 2, 4, 2)
        plus = QLabel("+")
        plus.setFixedWidth(14)
        new_row.addWidget(plus)
        new_row.addWidget(self.new_btn, 1)
        new_wrap = QWidget()
        new_wrap.setLayout(new_row)
        root.addWidget(new_wrap)

        self.setStyleSheet(
            """
            QLineEdit {
                background: #1a1a1e;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 6px 8px;
                color: #ececee;
            }
            QListWidget {
                background: transparent;
                color: #e0e0e0;
                outline: none;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-radius: 3px;
            }
            QListWidget::item:hover {
                background: #37373d;
                color: #ffffff;
            }
            QListWidget::item:selected {
                background: #094771;
                color: #ffffff;
            }
            QPushButton {
                text-align: left;
                color: #e0e0e0;
                padding: 4px 0;
                border: none;
            }
            QPushButton:hover {
                color: #ffffff;
            }
            QLabel {
                color: #e0e0e0;
                font-weight: 600;
            }
            """
        )

    def focus_search(self) -> None:
        self.search.setFocus(Qt.PopupFocusReason)
        self.search.selectAll()

    def _apply_filter(self, text: str) -> None:
        needle = text.strip().casefold()
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            if item is None:
                continue
            item.setHidden(bool(needle) and needle not in item.text().casefold())

    def _activate_first_visible(self) -> None:
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            if item is not None and not item.isHidden():
                self.playlist_chosen.emit(item.text())
                return
