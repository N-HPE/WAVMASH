"""Collapsible panel — click header to show/hide content."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class CollapsibleSection(QWidget):
    """Header toggle + content area that expands/collapses."""

    expanded_changed = Signal(bool)

    def __init__(
        self,
        title: str,
        content: QWidget,
        *,
        expanded: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("collapsibleSection")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._toggle = QToolButton()
        self._toggle.setObjectName("collapsibleToggle")
        self._toggle.setCheckable(True)
        self._toggle.setChecked(expanded)
        self._toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._toggle.setCursor(Qt.PointingHandCursor)
        self._toggle.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._toggle.clicked.connect(self._on_clicked)

        header = QFrame()
        header.setObjectName("collapsibleHeader")
        header_lay = QHBoxLayout(header)
        header_lay.setContentsMargins(4, 2, 4, 2)
        header_lay.addWidget(self._toggle)

        self._content = content
        self._content.setVisible(expanded)

        root.addWidget(header)
        root.addWidget(self._content)

        self._title = title
        self._sync_label()

    def is_expanded(self) -> bool:
        return self._toggle.isChecked()

    def set_expanded(self, expanded: bool) -> None:
        if self._toggle.isChecked() == expanded:
            return
        self._toggle.setChecked(expanded)
        self._apply_state(expanded)

    def _sync_label(self) -> None:
        arrow = "▼" if self._toggle.isChecked() else "▶"
        self._toggle.setText(f"{arrow}  {self._title}")

    def _on_clicked(self) -> None:
        self._apply_state(self._toggle.isChecked())

    def _apply_state(self, expanded: bool) -> None:
        self._content.setVisible(expanded)
        self._sync_label()
        self.expanded_changed.emit(expanded)
