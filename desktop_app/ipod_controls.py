"""iPod-style transport (vector icons) + responsive transport bar."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QPainter, QBrush, QPainterPath
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSizePolicy


class IPodIconButton(QWidget):
    """Skip / play / pause drawn with QPainter (no system emoji glyphs)."""

    clicked = Signal()

    def __init__(self, role: str, diameter: int, parent=None):
        super().__init__(parent)
        self._role = role
        self._diameter = diameter
        self._playing = False
        self._hover = False
        self._pressed = False
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self._apply_size()

    def _apply_size(self) -> None:
        d = self._diameter
        if self._role == "play":
            self.setFixedSize(d, d)
        else:
            s = max(28, int(d * 0.72))
            self.setFixedSize(s, s)

    def set_diameter(self, diameter: int) -> None:
        diameter = max(28, int(diameter))
        if diameter == self._diameter:
            return
        self._diameter = diameter
        self._apply_size()
        self.update()

    def set_playing(self, playing: bool) -> None:
        if self._role != "play":
            return
        if self._playing != playing:
            self._playing = playing
            self.update()

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._pressed = True
            self.update()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._pressed:
            self._pressed = False
            self.update()
            if self.rect().contains(event.position().toPoint()):
                self.clicked.emit()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        scale = self._diameter / 50.0

        if self._role == "play":
            r = min(w, h) / 2 - 2
            if self._pressed:
                fill = QColor("#a8a8ad")
            elif self._hover:
                fill = QColor("#ececee")
            else:
                fill = QColor("#d8d8dc")
            p.setPen(Qt.NoPen)
            p.setBrush(fill)
            p.drawEllipse(int(cx - r), int(cy - r), int(2 * r), int(2 * r))

            p.setBrush(QColor("#2c2c2e"))
            p.setPen(Qt.NoPen)
            if self._playing:
                bar_w = max(4, int(5 * scale))
                bar_h = max(12, int(16 * scale))
                gap = max(5, int(7 * scale))
                p.drawRoundedRect(int(cx - gap / 2 - bar_w), int(cy - bar_h / 2), bar_w, bar_h, 1, 1)
                p.drawRoundedRect(int(cx + gap / 2), int(cy - bar_h / 2), bar_w, bar_h, 1, 1)
            else:
                tri = max(8, int(11 * scale))
                path = QPainterPath()
                path.moveTo(cx - tri * 0.35, cy - tri)
                path.lineTo(cx + tri * 0.85, cy)
                path.lineTo(cx - tri * 0.35, cy + tri)
                path.closeSubpath()
                p.drawPath(path)
        else:
            if self._hover or self._pressed:
                p.setPen(Qt.NoPen)
                alpha = 90 if self._pressed else 55
                p.setBrush(QColor(255, 255, 255, alpha))
                p.drawRoundedRect(2, 2, w - 4, h - 4, 6, 6)

            icon = QColor("#c8c8cc" if self._hover else "#9a9a9e")
            p.setBrush(icon)
            p.setPen(Qt.NoPen)
            bar_h = max(10, int(14 * scale))
            bar_w = max(2, int(3 * scale))
            tri = max(5, int(7 * scale))
            if self._role == "prev":
                p.drawRect(int(cx + 4), int(cy - bar_h / 2), bar_w, bar_h)
                path = QPainterPath()
                path.moveTo(cx + 1, cy)
                path.lineTo(cx - tri, cy - tri * 0.9)
                path.lineTo(cx - tri, cy + tri * 0.9)
                path.closeSubpath()
                p.drawPath(path)
                path2 = QPainterPath()
                path2.moveTo(cx - tri - 5, cy)
                path2.lineTo(cx - tri * 2 - 4, cy - tri * 0.9)
                path2.lineTo(cx - tri * 2 - 4, cy + tri * 0.9)
                path2.closeSubpath()
                p.drawPath(path2)
            else:
                p.drawRect(int(cx - 7), int(cy - bar_h / 2), bar_w, bar_h)
                path = QPainterPath()
                path.moveTo(cx - 1, cy)
                path.lineTo(cx + tri, cy - tri * 0.9)
                path.lineTo(cx + tri, cy + tri * 0.9)
                path.closeSubpath()
                p.drawPath(path)
                path2 = QPainterPath()
                path2.moveTo(cx + tri + 5, cy)
                path2.lineTo(cx + tri * 2 + 4, cy - tri * 0.9)
                path2.lineTo(cx + tri * 2 + 4, cy + tri * 0.9)
                path2.closeSubpath()
                p.drawPath(path2)
        p.end()


class IPodTransportBar(QWidget):
    """Horizontal prev / play / next with room to breathe."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ipodWheel")
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Expanding)
        self.setMaximumWidth(240)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 8, 14, 8)
        lay.setSpacing(18)
        lay.setAlignment(Qt.AlignVCenter)

        self._play_d = 50
        self.prev_btn = IPodIconButton("prev", self._play_d, self)
        self.play_btn = IPodIconButton("play", self._play_d, self)
        self.next_btn = IPodIconButton("next", self._play_d, self)
        lay.addWidget(self.prev_btn)
        lay.addWidget(self.play_btn)
        lay.addWidget(self.next_btn)

        self.setMinimumWidth(200)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Scale center play button with available vertical space
        h = max(40, self.height() - 16)
        play_d = int(min(56, max(40, h * 0.88)))
        if play_d != self._play_d:
            self._play_d = play_d
            self.play_btn.set_diameter(play_d)
            self.prev_btn.set_diameter(play_d)
            self.next_btn.set_diameter(play_d)

    def sizeHint(self) -> QSize:
        return QSize(220, 64)
