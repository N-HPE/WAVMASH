import numpy as np
import scipy.io.wavfile as wavfile
from PySide6.QtCore import Qt, Signal, QSize, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QMouseEvent, QFont, QPolygonF, QWheelEvent
from PySide6.QtWidgets import QWidget, QSizePolicy

CUE_HIT_PX = 14


class WaveformWidget(QWidget):
    position_changed = Signal(float)  # percentage 0.0–1.0
    cues_changed = Signal()
    expand_requested = Signal()
    zoom_changed = Signal(float)

    SECTION_COLORS = {
        "intro": QColor(60, 70, 95),
        "build": QColor(80, 80, 110),
        "verse": QColor(55, 75, 70),
        "break": QColor(50, 60, 80),
        "chorus": QColor(110, 80, 50),
        "outro": QColor(70, 60, 70),
    }

    SECTION_LABELS = {
        "intro": "Intro",
        "build": "Build",
        "verse": "Verse",
        "break": "Break",
        "chorus": "Chorus",
        "outro": "Outro",
    }

    def __init__(self, parent=None, *, editor_mode: bool = False):
        super().__init__(parent)
        self.editor_mode = editor_mode
        self.setMinimumHeight(120 if editor_mode else 104)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.peaks = None
        self.progress = 0.0
        self.bg_color = QColor(30, 30, 30)
        self.played_color = QColor(0, 122, 204)
        self.unplayed_color = QColor(100, 100, 100)

        self.sections = None
        self.cue_in = None
        self.cue_out = None
        self.track_duration = None

        self._zoom = 1.0
        self._editable_cues = editor_mode
        self._drag_cue: str | None = None  # 'in' | 'out'
        self._hover_cue: str | None = None

        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)

    def set_zoom(self, factor: float) -> None:
        factor = max(1.0, min(32.0, float(factor)))
        if abs(factor - self._zoom) < 1e-6:
            return
        self._zoom = factor
        self._apply_zoom_geometry()
        self.zoom_changed.emit(self._zoom)
        self.update()

    def zoom(self) -> float:
        return self._zoom

    def set_editable_cues(self, enabled: bool) -> None:
        self._editable_cues = enabled
        self.update()

    def set_cues(self, cue_in: float | None, cue_out: float | None) -> None:
        self.cue_in = cue_in
        self.cue_out = cue_out
        self.update()

    def set_analysis(self, analysis):
        if not analysis:
            self.clear_analysis()
            return
        self.sections = analysis.get("sections") or []
        self.cue_in = analysis.get("cue_in")
        self.cue_out = analysis.get("cue_out")
        self.track_duration = analysis.get("duration")
        self._apply_zoom_geometry()
        self.update()

    def clear_analysis(self):
        self.sections = None
        self.cue_in = None
        self.cue_out = None
        self.track_duration = None
        self.update()

    def _base_width(self) -> int:
        p = self.parentWidget()
        while p is not None:
            from PySide6.QtWidgets import QScrollArea
            if isinstance(p, QScrollArea):
                return max(320, p.viewport().width())
            p = p.parentWidget()
        if self.parentWidget() is not None:
            return max(320, self.parentWidget().width())
        return 800

    def _apply_zoom_geometry(self) -> None:
        w = max(320, int(self._base_width() * self._zoom))
        self.setMinimumWidth(w)
        self.resize(w, max(self.height(), self.minimumHeight()))

    def _update_zoom_geometry(self):
        """Keep zoom width in sync when the scroll viewport resizes."""
        self._apply_zoom_geometry()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if event.oldSize().width() != event.size().width():
            self._apply_zoom_geometry()

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.ControlModifier:
            dy = event.angleDelta().y()
            if dy != 0:
                step = 1.12 if dy > 0 else 1.0 / 1.12
                self.set_zoom(self._zoom * step)
            event.accept()
            return
        super().wheelEvent(event)

    def load_audio(self, filepath: str):
        self.clear_analysis()
        try:
            sr, data = wavfile.read(filepath)
            if data.ndim > 1:
                data = data.mean(axis=1)

            num_bars = 1200 if self.editor_mode else 500
            samples_per_bar = max(1, len(data) // num_bars)
            truncated_len = num_bars * samples_per_bar
            data = np.abs(data[:truncated_len])
            reshaped = data.reshape((num_bars, samples_per_bar))
            peaks = np.max(reshaped, axis=1)

            max_peak = np.max(peaks)
            if max_peak > 0:
                peaks = peaks / max_peak
            else:
                peaks = np.zeros(num_bars)

            self.peaks = peaks
            if self.track_duration is None and sr:
                self.track_duration = len(data) / float(sr)
            self.progress = 0.0
            self._update_zoom_geometry()
            self.update()
        except Exception as e:
            print(f"Error loading waveform: {e}")
            self.peaks = None
            self.update()

    def set_progress(self, progress: float):
        self.progress = max(0.0, min(1.0, progress))
        self.update()

    def _time_to_x(self, t: float, width: int) -> float:
        if not self.track_duration or self.track_duration <= 0:
            return 0.0
        return max(0.0, min(1.0, t / self.track_duration)) * width

    def _x_to_time(self, x: float, width: int) -> float:
        if not self.track_duration or width <= 0:
            return 0.0
        return max(0.0, min(1.0, x / width)) * self.track_duration

    def _cue_hit(self, x: float, width: int) -> str | None:
        if not self._editable_cues or not self.track_duration:
            return None
        for key, t in (("in", self.cue_in), ("out", self.cue_out)):
            if t is None:
                continue
            cx = self._time_to_x(float(t), width)
            if abs(x - cx) <= CUE_HIT_PX:
                return key
        return None

    def _emit_cues(self):
        self.cues_changed.emit()

    def _clamp_cues(self):
        dur = float(self.track_duration or 0)
        if dur <= 0:
            return
        if self.cue_in is not None:
            self.cue_in = max(0.0, min(float(self.cue_in), dur))
        if self.cue_out is not None:
            self.cue_out = max(0.0, min(float(self.cue_out), dur))
        if self.cue_in is not None and self.cue_out is not None:
            if self.cue_out <= self.cue_in + 0.5:
                self.cue_out = min(dur, self.cue_in + 0.5)

    def add_cue_at(self, t: float) -> None:
        dur = float(self.track_duration or 0)
        if dur <= 0:
            return
        t = max(0.0, min(float(t), dur))
        if self.cue_in is None:
            self.cue_in = t
        elif self.cue_out is None:
            self.cue_out = t
        elif abs(t - float(self.cue_in)) <= abs(t - float(self.cue_out)):
            self.cue_in = t
        else:
            self.cue_out = t
        self._clamp_cues()
        self._emit_cues()
        self.update()

    def delete_cue(self) -> bool:
        if self.cue_out is not None:
            self.cue_out = None
        elif self.cue_in is not None:
            self.cue_in = None
        else:
            return False
        self._emit_cues()
        self.update()
        return True

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() != Qt.LeftButton or self.peaks is None:
            return
        w = self.width()
        x = event.position().x()
        hit = self._cue_hit(x, w)
        if hit:
            self._drag_cue = hit
            self.setCursor(Qt.SizeHorCursor)
            return
        self._handle_seek(x)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.peaks is None:
            return
        w = self.width()
        x = event.position().x()

        if self._drag_cue:
            t = self._x_to_time(x, w)
            if self._drag_cue == "in":
                self.cue_in = t
            else:
                self.cue_out = t
            self._clamp_cues()
            self.update()
            return

        if event.buttons() & Qt.LeftButton:
            self._handle_seek(x)
            return

        hover = self._cue_hit(x, w)
        if hover != self._hover_cue:
            self._hover_cue = hover
            self.setCursor(Qt.SizeHorCursor if hover else Qt.PointingHandCursor)
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self._drag_cue:
            self._drag_cue = None
            self._emit_cues()
            self.setCursor(Qt.PointingHandCursor)
        super().mouseReleaseEvent(event)

    def _handle_seek(self, x_pos: float):
        width = self.width()
        pct = max(0.0, min(1.0, x_pos / width))
        self.position_changed.emit(pct)

    def _format_time(self, sec: float) -> str:
        sec = max(0.0, sec)
        m = int(sec // 60)
        s = int(sec % 60)
        return f"{m}:{s:02d}"

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), self.bg_color)

        if self.peaks is None:
            painter.setPen(QColor("#666"))
            painter.drawText(self.rect(), Qt.AlignCenter, "오디오 없음")
            return

        width = self.width()
        height = self.height()
        label_h = 18 if self.editor_mode else 0

        if self.sections and self.track_duration:
            painter.setPen(Qt.NoPen)
            for s in self.sections:
                x0 = self._time_to_x(float(s.get("start", 0)), width)
                x1 = self._time_to_x(float(s.get("end", 0)), width)
                label = s.get("label", "")
                color = QColor(self.SECTION_COLORS.get(label, QColor(45, 45, 45)))
                color.setAlpha(160 if self.editor_mode else 150)
                painter.fillRect(int(x0), label_h, max(1, int(x1 - x0)), height - label_h, color)

                if self.editor_mode and int(x1 - x0) > 36:
                    painter.setPen(QColor(220, 220, 220, 180))
                    f = QFont()
                    f.setPixelSize(11)
                    f.setBold(True)
                    painter.setFont(f)
                    text = self.SECTION_LABELS.get(label, label)
                    painter.drawText(int(x0) + 4, label_h + 14, text)
                    painter.setPen(Qt.NoPen)

        num_bars = len(self.peaks)
        bar_width = width / num_bars
        split_idx = int(num_bars * self.progress)
        wave_top = label_h + 4
        wave_h = height - wave_top - 8

        for i, peak in enumerate(self.peaks):
            bar_height = max(2, int(peak * wave_h * 0.92))
            x = i * bar_width
            y = wave_top + (wave_h - bar_height) / 2
            painter.setBrush(self.played_color if i < split_idx else self.unplayed_color)
            painter.setPen(Qt.NoPen)
            painter.drawRect(int(x), int(y), max(1, int(bar_width - 0.5)), bar_height)

        if self.track_duration:
            self._draw_cue_marker(painter, self.cue_in, width, height, wave_top, wave_h,
                                   QColor(80, 220, 120), "CUE IN", "in")
            self._draw_cue_marker(painter, self.cue_out, width, height, wave_top, wave_h,
                                   QColor(240, 120, 90), "CUE OUT", "out")

        if self.progress > 0:
            px = int(width * self.progress)
            painter.setPen(QPen(QColor(255, 255, 255, 200), 1))
            painter.drawLine(px, wave_top, px, height - 4)

    def _draw_cue_marker(self, painter, t, width, height, wave_top, wave_h, color, label, key):
        if t is None:
            return
        x = int(self._time_to_x(float(t), width))
        active = self._drag_cue == key or self._hover_cue == key
        pen_w = 3 if active else 2
        painter.setPen(QPen(color, pen_w))
        painter.drawLine(x, wave_top, x, height - 4)

        tri = 7
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        path_y = height - 6
        painter.drawPolygon(QPolygonF([
            QPointF(x - tri, path_y),
            QPointF(x + tri, path_y),
            QPointF(x, path_y - tri),
        ]))

        if self.editor_mode or active:
            painter.setPen(color)
            f = QFont()
            f.setPixelSize(10)
            f.setBold(True)
            painter.setFont(f)
            time_str = self._format_time(float(t))
            painter.drawText(x + 6, wave_top + 12, f"{label}  {time_str}")
