"""Genre/tag display and tag-picker widgets for the track library UI."""
from __future__ import annotations

import hashlib

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QWidgetItem,
)


def genre_color(genre_name: str) -> str:
    if not genre_name:
        return "#555555"
    h = hashlib.md5(genre_name.encode("utf-8")).hexdigest()
    r = int(h[0:2], 16) % 128 + 127
    g = int(h[2:4], 16) % 128 + 127
    b = int(h[4:6], 16) % 128 + 127
    return f"#{r:02x}{g:02x}{b:02x}"


def tag_chip_qss(*, selected: bool = False) -> str:
    if selected:
        return (
            "QPushButton { color: #e8f0ff; background-color: rgba(0, 122, 204, 0.32);"
            " border: none; border-radius: 10px; padding: 4px 12px; font-size: 11px; font-weight: 600; }"
            "QPushButton:hover { background-color: rgba(0, 122, 204, 0.42); }"
        )
    return (
        "QPushButton { color: #9a9aa3; background-color: rgba(255, 255, 255, 0.07);"
        " border: none; border-radius: 10px; padding: 4px 12px; font-size: 11px; font-weight: 500; }"
        "QPushButton:hover { color: #c8c8d0; background-color: rgba(255, 255, 255, 0.10); }"
    )


class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self.itemList = []

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if index >= 0 and index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index):
        if index >= 0 and index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self.doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in list(self.itemList):
            try:
                if item.widget() is None:
                    continue
                size = size.expandedTo(item.minimumSize())
            except RuntimeError:
                self.itemList.remove(item)

        margin, _, _, _ = self.getContentsMargins()
        size += QSize(2 * margin, 2 * margin)
        return size

    def doLayout(self, rect, testOnly):
        x = rect.x()
        y = rect.y()
        lineHeight = 0

        for item in list(self.itemList):
            try:
                if item.widget() is None:
                    continue

                spaceX = self.spacing()
                spaceY = self.spacing()
                nextX = x + item.sizeHint().width() + spaceX
                if nextX - spaceX > rect.right() and lineHeight > 0:
                    x = rect.x()
                    y = y + lineHeight + spaceY
                    nextX = x + item.sizeHint().width() + spaceX
                    lineHeight = 0

                if not testOnly:
                    item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

                x = nextX
                lineHeight = max(lineHeight, item.sizeHint().height())
            except RuntimeError:
                self.itemList.remove(item)

        return y + lineHeight - rect.y()


class TagInputWidget(QWidget):
    def __init__(self, all_existing_tags, current_tags, parent=None):
        super().__init__(parent)
        self.all_tags = sorted(list(set(all_existing_tags)))
        self.current_tags = set(current_tags)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.flow_widget = QWidget()
        self.flow_layout = FlowLayout(self.flow_widget, spacing=6)

        self.chip_buttons = {}
        for tag in self.all_tags:
            btn = self._create_chip(tag)
            self.chip_buttons[tag] = btn
            self.flow_layout.addItem(QWidgetItem(btn))

        layout.addWidget(self.flow_widget)

        input_layout = QHBoxLayout()
        self.new_tag_input = QLineEdit()
        self.new_tag_input.setPlaceholderText("새로운 태그 입력 후 엔터...")
        self.new_tag_input.returnPressed.connect(self.add_new_tag)
        input_layout.addWidget(self.new_tag_input)

        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self.add_new_tag)
        input_layout.addWidget(add_btn)

        layout.addLayout(input_layout)

    def _create_chip(self, tag: str) -> QPushButton:
        btn = QPushButton(tag, self.flow_widget)
        btn.setCheckable(True)
        if tag in self.current_tags:
            btn.setChecked(True)
            btn.setStyleSheet(tag_chip_qss(selected=True))
        else:
            btn.setStyleSheet(tag_chip_qss(selected=False))

        btn.toggled.connect(lambda checked, t=tag, b=btn: self._on_chip_toggled(checked, t, b))
        return btn

    def _on_chip_toggled(self, checked, tag, btn):
        if checked:
            self.current_tags.add(tag)
            btn.setStyleSheet(tag_chip_qss(selected=True))
        else:
            self.current_tags.discard(tag)
            btn.setStyleSheet(tag_chip_qss(selected=False))

    def add_new_tag(self):
        tag = self.new_tag_input.text().strip()
        if not tag:
            return
        if tag not in self.all_tags:
            self.all_tags.append(tag)
            btn = self._create_chip(tag)
            self.chip_buttons[tag] = btn
            self.flow_layout.addItem(QWidgetItem(btn))
            btn.setChecked(True)
        elif tag in self.chip_buttons:
            self.chip_buttons[tag].setChecked(True)

        self.new_tag_input.clear()

    def get_selected_tags(self) -> list:
        return sorted(list(self.current_tags))


class GenreTagsWidget(QWidget):
    def __init__(self, genre: str, tags: list, parent=None):
        super().__init__(parent)
        self.flow_layout = FlowLayout(self, margin=4, spacing=6)

        if genre:
            color = genre_color(genre)
            genre_label = QLabel(f"<span style='color:{color};'>●</span> {genre}", self)
            genre_label.setStyleSheet(
                "font-weight: 600; color: #e4e4ea; background: transparent; padding: 2px 0;"
            )
            self.flow_layout.addItem(QWidgetItem(genre_label))

        for tag in tags:
            tag_label = QLabel(tag, self)
            tag_label.setStyleSheet(
                "color: #a0a0aa; background: rgba(255, 255, 255, 0.06);"
                " border: none; border-radius: 6px; padding: 1px 7px; font-size: 11px;"
            )
            self.flow_layout.addItem(QWidgetItem(tag_label))

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
