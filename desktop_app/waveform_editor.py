"""Expanded waveform view — zoom, section labels, draggable CUE IN / CUE OUT."""
from __future__ import annotations

import copy
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from desktop_app.waveform import WaveformWidget


class WaveformEditorDialog(QDialog):
    def __init__(self, record: dict[str, Any], parent=None):
        super().__init__(parent)
        self.record = record
        self._analysis = copy.deepcopy(record.get("analysis") or {})
        self._dirty = False

        title = record.get("title", "")
        artist = record.get("artist", "")
        self.setWindowTitle(f"웨이브 · Cue 편집 — {artist} - {title}".strip(" -"))
        self.resize(960, 420)

        root = QVBoxLayout(self)
        root.setSpacing(10)

        hint = QLabel(
            "Ctrl+휠: 확대/축소 · 섹션 색으로 Intro/Chorus/Outro 확인 · "
            "초록(CUE IN) · 주황(CUE OUT) 마커를 드래그해 조정"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #aaa; font-size: 12px;")
        root.addWidget(hint)

        legend = QHBoxLayout()
        for label, color in (
            ("Intro", "#3c465f"),
            ("Chorus", "#6e5032"),
            ("Outro", "#463c46"),
            ("CUE IN", "#50dc78"),
            ("CUE OUT", "#f0785a"),
        ):
            chip = QLabel(f"  {label}  ")
            chip.setStyleSheet(
                f"background:{color}; color:#eee; border-radius:4px; "
                f"padding:2px 6px; font-size:11px;"
            )
            legend.addWidget(chip)
        legend.addStretch(1)
        root.addLayout(legend)

        zoom_row = QHBoxLayout()
        zoom_row.addWidget(QLabel("확대"))
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(1)
        self.zoom_slider.setMaximum(16)
        self.zoom_slider.setValue(4)
        self.zoom_slider.setFixedWidth(160)
        self.zoom_slider.valueChanged.connect(self._on_zoom)
        zoom_row.addWidget(self.zoom_slider)
        self.zoom_label = QLabel("4×")
        zoom_row.addWidget(self.zoom_label)
        zoom_row.addStretch(1)
        self.cue_info = QLabel("")
        self.cue_info.setStyleSheet("color: #ccc; font-size: 12px;")
        zoom_row.addWidget(self.cue_info)
        root.addLayout(zoom_row)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(False)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setMinimumHeight(200)

        self.wave = WaveformWidget(editor_mode=True)
        self.wave.set_editable_cues(True)
        path = str(record.get("path", ""))
        if path:
            self.wave.load_audio(path)
        self.wave.set_analysis(self._analysis)
        self.wave.set_zoom(4)
        self.wave.cues_changed.connect(self._on_cues_changed)
        self.wave.position_changed.connect(self._on_seek)
        self.wave.zoom_changed.connect(self._on_wave_zoom_changed)
        self.scroll.setWidget(self.wave)
        root.addWidget(self.scroll, 1)

        btns = QHBoxLayout()
        btns.addStretch(1)
        self.reset_btn = QPushButton("분석값으로 되돌리기")
        self.reset_btn.clicked.connect(self._reset_cues)
        btns.addWidget(self.reset_btn)
        self.cancel_btn = QPushButton("취소")
        self.cancel_btn.clicked.connect(self.reject)
        btns.addWidget(self.cancel_btn)
        self.save_btn = QPushButton("저장")
        self.save_btn.setObjectName("primary")
        self.save_btn.clicked.connect(self._save)
        btns.addWidget(self.save_btn)
        root.addLayout(btns)

        self._refresh_cue_label()

    def _on_zoom(self, v: int):
        self._set_zoom_slider(v, from_slider=True)

    def _on_wave_zoom_changed(self, factor: float):
        v = max(1, min(16, int(round(factor))))
        self._set_zoom_slider(v, from_slider=False)

    def _set_zoom_slider(self, v: int, *, from_slider: bool):
        self.zoom_label.setText(f"{v}×")
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(v)
        self.zoom_slider.blockSignals(False)
        if from_slider:
            self.wave.set_zoom(float(v))

    def _on_cues_changed(self):
        ci = self.wave.cue_in
        co = self.wave.cue_out
        if ci is not None:
            self._analysis["cue_in"] = round(float(ci), 3)
        if co is not None:
            self._analysis["cue_out"] = round(float(co), 3)
        self._dirty = True
        self._refresh_cue_label()

    def _on_seek(self, pct: float):
        self.wave.set_progress(pct)

    def _refresh_cue_label(self):
        ci = self._analysis.get("cue_in")
        co = self._analysis.get("cue_out")
        if ci is not None and co is not None:
            self.cue_info.setText(f"CUE IN {self._fmt(ci)}  →  CUE OUT {self._fmt(co)}")
        else:
            self.cue_info.setText("Cue 없음 — 구조 분석을 먼저 실행하세요")

    @staticmethod
    def _fmt(sec: float) -> str:
        sec = max(0.0, float(sec))
        return f"{int(sec // 60)}:{int(sec % 60):02d}"

    def _reset_cues(self):
        orig = self.record.get("analysis") or {}
        for k in ("cue_in", "cue_out"):
            if k in orig:
                self._analysis[k] = orig[k]
        self.wave.set_analysis(self._analysis)
        self._dirty = False
        self._refresh_cue_label()

    def _save(self):
        if not self._analysis:
            self.reject()
            return
        self.accept()

    def updated_analysis(self) -> dict | None:
        return copy.deepcopy(self._analysis) if self._dirty else None
