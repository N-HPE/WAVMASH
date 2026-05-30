from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import hashlib
from typing import Any

from PySide6.QtCore import Qt, QSize, QUrl, QTimer, QRect, QPoint, QMimeData
from PySide6.QtGui import (
    QAction,
    QIcon,
    QPalette,
    QColor,
    QPixmap,
    QPainter,
    QPainterPath,
    QFontMetrics,
    QDrag,
    QClipboard,
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QSystemTrayIcon,
    QMenu,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QFormLayout,
    QHeaderView,
    QLayout,
    QWidgetItem,
    QCheckBox,
    QSlider,
    QSizePolicy,
    QScrollArea,
    QAbstractItemView,
)

from desktop_app.archive_store import delete_record, load_archive, upsert_record, save_archive
from desktop_app.single_instance import SingleInstanceGuard, try_activate_existing_instance
from desktop_app.workers import JobRequest, WorkerPool
from desktop_app.waveform import WaveformWidget
from desktop_app.ipod_controls import IPodTransportBar
from paths import PROJECT_DIR
from library import (
    WAV_ROOT,
    cleanup_empty_dirs,
    delete_track_file,
    find_cover_sidecar,
    needs_bpm_key_update,
    read_cover_bytes_for_wav,
    repair_missing_covers,
    resolve_cover_bytes,
    write_wav_tags,
    split_version,
    version_group_key,
)

CAMELOT_WHEEL = {
    # Major (B)
    "B Major": "1B", "F# Major": "2B", "C# Major": "3B", "G# Major": "4B", 
    "D# Major": "5B", "A# Major": "6B", "F Major": "7B", "C Major": "8B", 
    "G Major": "9B", "D Major": "10B", "A Major": "11B", "E Major": "12B",
    # Minor (A)
    "G# Minor": "1A", "D# Minor": "2A", "A# Minor": "3A", "F Minor": "4A",
    "C Minor": "5A", "G Minor": "6A", "D Minor": "7A", "A Minor": "8A",
    "E Minor": "9A", "B Minor": "10A", "F# Minor": "11A", "C# Minor": "12A",
    # Fallback for old records without Major/Minor
    "B": "1B", "F#": "2B", "C#": "3B", "G#": "4B", "D#": "5B", "A#": "6B", 
    "F": "7B", "C": "8B", "G": "9B", "D": "10B", "A": "11B", "E": "12B"
}

CAMELOT_COLORS = {
    "1A": "#00EBA9", "1B": "#00EB62",
    "2A": "#62EBA9", "2B": "#62EB62",
    "3A": "#62EB00", "3B": "#00EB00",
    "4A": "#C8EB00", "4B": "#A9EB00",
    "5A": "#EBA900", "5B": "#EBC800",
    "6A": "#EB6200", "6B": "#EB9400",
    "7A": "#EB0000", "7B": "#EB0031",
    "8A": "#EB0062", "8B": "#EB0094",
    "9A": "#EB00C8", "9B": "#EB00EB",
    "10A": "#A900EB", "10B": "#6200EB",
    "11A": "#6262EB", "11B": "#0062EB",
    "12A": "#00A9EB", "12B": "#00EBEB",
}

_DARK_MENU_QSS = """
    QMenu {
        background-color: #2d2d2d;
        color: #e0e0e0;
        border: 1px solid #555555;
        padding: 4px 0;
    }
    QMenu::item {
        padding: 6px 28px 6px 16px;
        color: #e0e0e0;
    }
    QMenu::item:selected {
        background-color: #094771;
        color: #ffffff;
    }
    QMenu::item:disabled {
        color: #888888;
    }
    QMenu::separator {
        height: 1px;
        background: #555555;
        margin: 4px 10px;
    }
"""


def _style_context_menu(menu: QMenu) -> None:
    menu.setStyleSheet(_DARK_MENU_QSS)
    for action in menu.actions():
        sub = action.menu()
        if sub is not None:
            _style_context_menu(sub)


def cover_pixmap_for_path(wav_path: str, size: int) -> QPixmap | None:
    """Load a scaled square cover from sidecar or embedded WAV art."""
    if not wav_path:
        return None
    sidecar = find_cover_sidecar(wav_path)
    if sidecar:
        pm = QPixmap(sidecar)
        if not pm.isNull():
            return pm.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    data, _mime = read_cover_bytes_for_wav(wav_path)
    if data:
        pm = QPixmap()
        if pm.loadFromData(data):
            return pm.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    return None


class TrackWidget(QWidget):
    def __init__(self, wav_path, title, artist, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(40, 40)
        self.cover_label.setStyleSheet("background-color: #333; border-radius: 4px;")
        
        pixmap = cover_pixmap_for_path(wav_path, 40)
        if pixmap is not None and not pixmap.isNull():
            self.cover_label.setPixmap(pixmap)
            
        layout.addWidget(self.cover_label)
        
        vbox = QVBoxLayout()
        vbox.setContentsMargins(8, 2, 0, 2)
        vbox.setSpacing(2)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; color: white; font-size: 13px; background: transparent;")
        
        artist_label = QLabel(artist)
        artist_label.setStyleSheet("color: #aaaaaa; font-size: 11px; background: transparent;")
        
        vbox.addWidget(title_label)
        vbox.addWidget(artist_label)
        vbox.addStretch()
        
        layout.addLayout(vbox)
        
        # Make sure double clicks on this widget pass through to the table
        self.setAttribute(Qt.WA_TransparentForMouseEvents)


class TrackTableWidget(QTableWidget):
    """Track list with OS file drag (Explorer, Ableton, folders)."""

    INTERNAL_TRACK_MIME = "application/x-wavemash-track-ids"

    def __init__(self, owner: "MainWindow", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._owner = owner

    def startDrag(self, supportedActions):
        recs = self._owner.selected_records()
        track_ids = [str(r.get("id", "")) for r in recs if r.get("id")]
        paths = self._owner.selected_file_paths()
        urls = [QUrl.fromLocalFile(os.path.normpath(p)) for p in paths if os.path.isfile(p)]

        mime = QMimeData()
        if urls:
            mime.setUrls(urls)
        if track_ids:
            mime.setData(self.INTERNAL_TRACK_MIME, ",".join(track_ids).encode("utf-8"))

        if not mime.hasUrls() and not mime.hasFormat(self.INTERNAL_TRACK_MIME):
            return super().startDrag(supportedActions)

        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.CopyAction)


class MiniTrackDragWidget(QWidget):
    """Mini-mode draggable cover — drop WAV files into Ableton, folders, etc."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(54, 54)
        self.setCursor(Qt.OpenHandCursor)
        self.setToolTip("마지막 다운로드 곡 — 드래그해서 Ableton/폴더에 놓기 (더블클릭: 복사)")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.cover = QLabel()
        self.cover.setFixedSize(48, 48)
        self.cover.setAlignment(Qt.AlignCenter)
        self.cover.setStyleSheet(
            "background-color: #2a2a2e; border: 1px solid #555; border-radius: 6px; color: #666; font-size: 18px;"
        )
        self.cover.setText("♪")
        layout.addWidget(self.cover, 0, Qt.AlignCenter)

        self._paths: list[str] = []
        self._track_ids: list[str] = []
        self._drag_start: QPoint | None = None
        self.hide()

    def set_records(self, records: list[dict[str, Any]]) -> None:
        self._paths = []
        self._track_ids = []
        first: dict[str, Any] | None = None
        for rec in records:
            if not isinstance(rec, dict):
                continue
            path = os.path.normpath(str(rec.get("path") or ""))
            if path and os.path.isfile(path):
                self._paths.append(path)
                tid = str(rec.get("id") or "")
                if tid:
                    self._track_ids.append(tid)
                if first is None:
                    first = rec

        if not self._paths or first is None:
            self.cover.clear()
            self.cover.setText("♪")
            self.setToolTip("다운로드 후 여기서 드래그")
            self.setEnabled(False)
            return

        self.setEnabled(True)
        pixmap = cover_pixmap_for_path(self._paths[0], 48)
        if pixmap is not None and not pixmap.isNull():
            self.cover.setText("")
            self.cover.setPixmap(pixmap)
        else:
            self.cover.setPixmap(QPixmap())
            self.cover.setText("♪")

        title = str(first.get("title") or "")
        artist = str(first.get("artist") or "")
        count = len(self._paths)
        if count > 1:
            tip = f"{title}\n{artist}\n\n{count}곡 — 드래그 → Ableton / 폴더"
        else:
            tip = f"{title}\n{artist}\n\n드래그 → Ableton / 폴더"
        self.setToolTip(tip)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self._paths:
            self._drag_start = event.position().toPoint()
            self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_start = None
        self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if not (event.buttons() & Qt.LeftButton) or not self._paths or self._drag_start is None:
            return
        if (event.position().toPoint() - self._drag_start).manhattanLength() < QApplication.startDragDistance():
            return
        self._drag_start = None
        self.setCursor(Qt.OpenHandCursor)

        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(p) for p in self._paths if os.path.isfile(p)])
        if self._track_ids:
            mime.setData(
                TrackTableWidget.INTERNAL_TRACK_MIME,
                ",".join(self._track_ids).encode("utf-8"),
            )

        drag = QDrag(self)
        drag.setMimeData(mime)
        pm = self.cover.pixmap()
        if pm is not None and not pm.isNull():
            drag.setPixmap(pm.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            drag.setHotSpot(QPoint(20, 20))
        drag.exec(Qt.CopyAction)

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self._paths:
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(p) for p in self._paths if os.path.isfile(p)])
            QApplication.clipboard().setMimeData(mime, QClipboard.Clipboard)
            win = self.window()
            if hasattr(win, "status"):
                n = len(self._paths)
                win.status.setText(
                    f"파일 {n}개 복사됨 — Ctrl+V" if n > 1 else "파일 복사됨 — Ctrl+V"
                )
        super().mouseDoubleClickEvent(event)


def get_genre_color(genre_name: str) -> str:
    if not genre_name:
        return "#555555"
    h = hashlib.md5(genre_name.encode('utf-8')).hexdigest()
    r = int(h[0:2], 16) % 128 + 127
    g = int(h[2:4], 16) % 128 + 127
    b = int(h[4:6], 16) % 128 + 127
    return f"#{r:02x}{g:02x}{b:02x}"

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
        height = self.doLayout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in list(self.itemList):
            try:
                if item.widget() is None: continue
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
                wid = item.widget()
                if wid is None: continue
                
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
            btn = self.create_chip(tag)
            self.chip_buttons[tag] = btn
            self.flow_layout.addItem(QWidgetItem(btn))
            
        layout.addWidget(self.flow_widget)
        
        input_layout = QHBoxLayout()
        self.new_tag_input = QLineEdit()
        self.new_tag_input.setPlaceholderText("새로운 태그 입력 후 엔터...")
        self.new_tag_input.returnPressed.connect(self.add_new_tag)
        input_layout.addWidget(self.new_tag_input)
        
        add_btn = QPushButton("추가")
        add_btn.clicked.connect(self.add_new_tag)
        input_layout.addWidget(add_btn)
        
        layout.addLayout(input_layout)

    def create_chip(self, tag: str) -> QPushButton:
        btn = QPushButton(tag, self.flow_widget)
        btn.setCheckable(True)
        if tag in self.current_tags:
            btn.setChecked(True)
            btn.setStyleSheet("background-color: rgba(0, 122, 204, 0.5); color: #fff; border-radius: 12px; padding: 4px 12px;")
        else:
            btn.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); color: #aaa; border-radius: 12px; padding: 4px 12px;")
            
        btn.toggled.connect(lambda checked, t=tag, b=btn: self.on_chip_toggled(checked, t, b))
        return btn
        
    def on_chip_toggled(self, checked, tag, btn):
        if checked:
            self.current_tags.add(tag)
            btn.setStyleSheet("background-color: rgba(0, 122, 204, 0.5); color: #fff; border-radius: 12px; padding: 4px 12px;")
        else:
            self.current_tags.discard(tag)
            btn.setStyleSheet("background-color: rgba(255, 255, 255, 0.1); color: #aaa; border-radius: 12px; padding: 4px 12px;")

    def add_new_tag(self):
        tag = self.new_tag_input.text().strip()
        if not tag:
            return
        if tag not in self.all_tags:
            self.all_tags.append(tag)
            btn = self.create_chip(tag)
            self.chip_buttons[tag] = btn
            self.flow_layout.addItem(QWidgetItem(btn))
            btn.setChecked(True)
        else:
            if tag in self.chip_buttons:
                self.chip_buttons[tag].setChecked(True)
                
        self.new_tag_input.clear()
        
    def get_selected_tags(self) -> list:
        return sorted(list(self.current_tags))

class GenreTagsWidget(QWidget):
    def __init__(self, genre: str, tags: list, parent=None):
        super().__init__(parent)
        self.flow_layout = FlowLayout(self, margin=4, spacing=6)
        
        if genre:
            color = get_genre_color(genre)
            genre_label = QLabel(f"<span style='color:{color};'>●</span> {genre}", self)
            genre_label.setStyleSheet("font-weight: bold; color: white; background: transparent; padding: 2px;")
            self.flow_layout.addItem(QWidgetItem(genre_label))
            
        for tag in tags:
            tag_label = QLabel(tag, self)
            tag_label.setStyleSheet("background-color: rgba(255, 255, 255, 0.15); color: #ddd; border-radius: 10px; padding: 2px 8px; font-size: 11px;")
            self.flow_layout.addItem(QWidgetItem(tag_label))
            
        self.setAttribute(Qt.WA_TransparentForMouseEvents)


def _open_in_explorer(path: str) -> None:
    if not path:
        return
    if os.path.exists(path):
        subprocess.Popen(f'explorer /select,"{os.path.normpath(path)}"')
    else:
        subprocess.Popen(f'explorer "{os.path.normpath(WAV_ROOT)}"')


class BulkEditDialog(QDialog):
    def __init__(self, records: list[dict[str, Any]], all_existing_tags: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setModal(True)
        self.resize(600, 450)
        self.setMinimumWidth(500)
        self.records = records
        self.all_existing_tags = all_existing_tags

        layout = QVBoxLayout(self)

        if len(records) == 1:
            self.setWindowTitle("태그 편집")
            layout.addWidget(QLabel("1개의 곡을 선택하셨습니다."))
        else:
            self.setWindowTitle("다중 태그 편집")
            layout.addWidget(QLabel(f"{len(records)}개의 곡을 선택하셨습니다."))

        form = QFormLayout()
        self.artist_edit = QLineEdit()
        self.album_edit = QLineEdit()
        self.genre_edit = QComboBox()
        self.genre_edit.setEditable(True)
        self.genre_edit.addItems([
            "", "Pop", "Dance", "Electronic", "Classical", "Jazz", 
            "Hip-Hop", "R&B", "Rock", "Latin", "Country", 
            "K-Pop", "J-Pop", "Indie", "Ambient", "Acoustic"
        ])
        self.genre_edit.lineEdit().setPlaceholderText("메인 장르 선택 또는 입력...")
        
        if len(records) == 1:
            self.artist_edit.setText(records[0].get("artist", ""))
            self.album_edit.setText(records[0].get("album", ""))
            self.genre_edit.setCurrentText(records[0].get("genre", ""))

        form.addRow("Artist:", self.artist_edit)
        form.addRow("Album:", self.album_edit)
        form.addRow("Main Genre:", self.genre_edit)
        layout.addLayout(form)
        
        layout.addWidget(QLabel("특징 태그 (Tags):"))
        
        all_tags = []
        for r in records:
            all_tags.extend(r.get("tags", []))
            
        # If we want all tags from ALL records globally, we should pass it in. 
        # But for now, we'll extract from the selected ones, or we can pass MainWindow's records.
        # Actually, it's better to pass all_existing_tags to BulkEditDialog.
        
        self.tag_input = TagInputWidget(self.all_existing_tags, set(all_tags))
        layout.addWidget(self.tag_input)

        buttons = QHBoxLayout()
        cancel = QPushButton("취소")
        ok = QPushButton("적용")
        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self.accept)
        buttons.addStretch(1)
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        layout.addLayout(buttons)

    def get_updates(self) -> dict[str, Any]:
        updates = {}
        if self.artist_edit.text().strip():
            updates["artist"] = self.artist_edit.text().strip()
        if self.album_edit.text().strip():
            updates["album"] = self.album_edit.text().strip()
        if self.genre_edit.currentText().strip():
            updates["genre"] = self.genre_edit.currentText().strip()
            
        updates["tags"] = self.tag_input.get_selected_tags()
        return updates


class VersionFinderDialog(QDialog):
    """Search YouTube and pick which videos to download."""

    def __init__(
        self,
        pool: WorkerPool,
        initial_query: str,
        parent: QWidget | None = None,
        *,
        title: str = "YouTube 검색",
        hint: str = "검색어를 입력하고 받을 영상을 체크하세요.",
        ok_label: str = "선택 다운로드",
    ) -> None:
        super().__init__(parent)
        self.pool = pool
        self.selected: list[dict[str, Any]] = []
        self.setWindowTitle(title)
        self.resize(580, 440)

        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        self.query_edit = QLineEdit(initial_query)
        self.query_edit.setPlaceholderText("아티스트, 곡명, 키워드...")
        self.search_btn = QPushButton("검색")
        row.addWidget(self.query_edit, 1)
        row.addWidget(self.search_btn)
        lay.addLayout(row)

        self.hint = QLabel(hint)
        self.hint.setWordWrap(True)
        lay.addWidget(self.hint)

        self.list = QListWidget()
        lay.addWidget(self.list, 1)

        btns = QHBoxLayout()
        btns.addStretch(1)
        self.cancel_btn = QPushButton("취소")
        self.ok_btn = QPushButton(ok_label)
        btns.addWidget(self.cancel_btn)
        btns.addWidget(self.ok_btn)
        lay.addLayout(btns)

        self.search_btn.clicked.connect(self.do_search)
        self.query_edit.returnPressed.connect(self.do_search)
        self.cancel_btn.clicked.connect(self.reject)
        self.ok_btn.clicked.connect(self.accept_selection)

        if initial_query.strip():
            self.do_search()

    def do_search(self) -> None:
        query = self.query_edit.text().strip()
        if not query:
            return
        self.list.clear()
        self.search_btn.setEnabled(False)
        self.hint.setText("YouTube 검색 중…")
        job = self.pool.start_version_search(query, 12)
        job.signals.results.connect(self.on_results)
        job.signals.failed.connect(self.on_search_failed)

    def on_results(self, results: list) -> None:
        self.search_btn.setEnabled(True)
        if not results:
            self.hint.setText("결과가 없습니다. 검색어를 바꿔보세요.")
            return
        self.hint.setText(f"{len(results)}개 결과 — 받을 영상을 체크하세요.")
        for c in results:
            dur = int(c.get("duration") or 0)
            dur_str = f"{dur // 60}:{dur % 60:02d}" if dur else "?:??"
            uploader = c.get("uploader") or ""
            item = QListWidgetItem(f"[{dur_str}]  {c.get('title', '')}   ·  {uploader}")
            item.setData(Qt.UserRole, c)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.list.addItem(item)

    def on_search_failed(self, err: str) -> None:
        self.search_btn.setEnabled(True)
        self.hint.setText(f"검색 실패: {err}")

    def accept_selection(self) -> None:
        chosen = []
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it.checkState() == Qt.Checked:
                chosen.append(it.data(Qt.UserRole))
        if not chosen:
            self.hint.setText("받을 영상을 하나 이상 체크해 주세요.")
            return
        self.selected = chosen
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("WaveMash")
        self.resize(1200, 750)
        
        self.icon_path = os.path.join(PROJECT_DIR, "icon_large.ico")
        if os.path.exists(self.icon_path):
            self.setWindowIcon(QIcon(self.icon_path))

        self.mini_mode = False
        self._saved_geometry = None
        self._metadata_job = None
        self._download_queue: list[tuple[str, str]] = []  # (source, url)
        self._download_active = False

        self.pool = WorkerPool()
        self.records: list[dict[str, Any]] = load_archive()
        from library import plan_track_path, reorganize_library

        needs_layout_fix = any(
            rec.get("path")
            and os.path.isfile(str(rec["path"]))
            and os.path.normcase(str(rec["path"]))
            != os.path.normcase(
                plan_track_path(
                    {
                        "artist": rec.get("artist", ""),
                        "primary_artist": rec.get("primary_artist"),
                        "album": rec.get("album", ""),
                        "title": rec.get("title", ""),
                    },
                    bpm=rec.get("bpm"),
                    key=rec.get("key"),
                )
            )
            for rec in self.records
        )
        if needs_layout_fix:
            self.records, moved = reorganize_library(self.records, refresh_metadata=False)
            if moved:
                save_archive(self.records)
        
        # Playlists state
        self.playlists_file = os.path.join(PROJECT_DIR, "playlists.json")
        self.playlists: dict[str, list[str]] = self.load_playlists()  # name -> list of track ids
        self.current_playlist = "All Tracks"
        
        self.show_camelot = False

        # Audio Player Setup (dual-deck for crossfade)
        self.audio_output_a = QAudioOutput()
        self.player_a = QMediaPlayer()
        self.player_a.setAudioOutput(self.audio_output_a)

        self.audio_output_b = QAudioOutput()
        self.player_b = QMediaPlayer()
        self.player_b.setAudioOutput(self.audio_output_b)

        for p in (self.player_a, self.player_b):
            p.positionChanged.connect(self.on_player_position_changed)
            p.durationChanged.connect(self.on_player_duration_changed)
            p.mediaStatusChanged.connect(self.on_media_status_changed)

        self.cur = "a"  # foreground deck currently holding the "now playing" track
        self.current_duration = 0

        # Playback queue
        self.play_queue: list[dict[str, Any]] = []
        self.queue_index = -1

        # Auto-mix settings / state
        self.autoplay_enabled = True
        self.crossfade_enabled = True
        self.crossfade_ms = 6000
        self.fading = False
        self.fade_timer = QTimer(self)
        self.fade_timer.setInterval(50)
        self.fade_timer.timeout.connect(self._on_fade_tick)
        self._fade_elapsed = 0
        self._fade_out_deck: str | None = None
        self._fade_in_deck: str | None = None
        self._pending_seek: tuple[str, int] | None = None  # (deck, position_ms) mix-in cue

        self.init_ui()
        self.init_tray()
        self.apply_dark_theme()

        job = self.pool.start_cover_repair(self.records)
        job.signals.finished.connect(self.on_covers_repaired)
        
        # Install global event filter for spacebar play/pause
        QApplication.instance().installEventFilter(self)

    def load_playlists(self) -> dict[str, list[str]]:
        if os.path.exists(self.playlists_file):
            try:
                with open(self.playlists_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_playlists(self) -> None:
        try:
            with open(self.playlists_file, "w", encoding="utf-8") as f:
                json.dump(self.playlists, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving playlists: {e}")

    def apply_dark_theme(self) -> None:
        # Professional Dark Theme (Mac-like)
        self.setStyleSheet("""
            QMainWindow, QDialog, QMessageBox {
                background-color: #1e1e1e;
            }
            QWidget {
                color: #e0e0e0;
                font-family: 'Segoe UI', system-ui, sans-serif;
                font-size: 13px;
            }
            QPushButton {
                background-color: #333333;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #444444;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
            QPushButton#primary {
                background-color: #007acc;
                border-color: #007acc;
                color: white;
            }
            QPushButton#primary:hover {
                background-color: #0098ff;
            }
            QPushButton#danger {
                background-color: #d83b01;
                border-color: #d83b01;
                color: white;
            }
            QPushButton#danger:hover {
                background-color: #f74502;
            }
            QPushButton#icon_btn {
                padding: 4px;
                font-weight: bold;
                font-size: 16px;
            }
            /* --- iPod Now Playing panel --- */
            QWidget#ipodPanel {
                background: transparent;
            }
            QLabel#ipodCover {
                background-color: #0a0a0b;
                border: 2px solid #4a4a4e;
                border-radius: 6px;
            }
            QWidget#playerPanel {
                border-top: 1px solid #333338;
            }
            QWidget#playerControlsStrip {
                background: transparent;
            }
            QWidget#ipodWheel {
                background-color: #2a2a2e;
                border: 1px solid #3d3d42;
                border-radius: 12px;
            }
            QLabel#npTitle {
                color: #ffffff;
                font-size: 15px;
                font-weight: 700;
                background: transparent;
                padding: 0px;
            }
            QLabel#npArtist {
                color: #a8a8ad;
                font-size: 13px;
                font-weight: 400;
                background: transparent;
                padding: 0px;
            }
            QWidget#npMeta {
                background: transparent;
            }
            QLineEdit, QComboBox {
                background-color: #2d2d2d;
                border: 1px solid #444444;
                border-radius: 4px;
                padding: 6px;
                color: #ffffff;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #007acc;
            }
            QTableWidget {
                background-color: #1e1e1e;
                border: 1px solid #333333;
                gridline-color: #333333;
                selection-background-color: #007acc;
                selection-color: #ffffff;
            }
            QHeaderView::section {
                background-color: #252526;
                color: #cccccc;
                padding: 4px;
                border: 1px solid #333333;
                border-left: none;
                border-top: none;
            }
            QListWidget {
                background-color: #252526;
                border: 1px solid #333333;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 8px;
            }
            QListWidget::item:selected {
                background-color: #37373d;
                border-left: 3px solid #007acc;
            }
            QMenu {
                background-color: #2d2d2d;
                color: #e0e0e0;
                border: 1px solid #555555;
                padding: 4px 0;
            }
            QMenu::item {
                padding: 6px 28px 6px 16px;
                background-color: transparent;
                color: #e0e0e0;
            }
            QMenu::item:selected {
                background-color: #094771;
                color: #ffffff;
            }
            QMenu::item:disabled {
                color: #888888;
            }
            QMenu::separator {
                height: 1px;
                background: #555555;
                margin: 4px 10px;
            }
            QProgressBar {
                border: 1px solid #444444;
                border-radius: 2px;
                background-color: #1e1e1e;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #007acc;
            }
        """)

    def init_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)

        # Top Ingest
        ingest_row = QHBoxLayout()
        outer.addLayout(ingest_row)

        self.mini_drag = MiniTrackDragWidget(self)
        ingest_row.addWidget(self.mini_drag)

        self.url = QLineEdit()
        self.url.setPlaceholderText("URL 또는 곡명 (YouTube 검색)...")
        ingest_row.addWidget(self.url, 1)

        self.yt_search_btn = QPushButton("검색")
        self.yt_search_btn.setToolTip("YouTube에서 곡 검색")
        self.yt_search_btn.clicked.connect(self.on_youtube_search)
        ingest_row.addWidget(self.yt_search_btn)

        self.download_plist = QComboBox()
        self.download_plist.setToolTip("다운로드한 곡을 자동으로 추가할 플레이리스트")
        self.download_plist.setMinimumWidth(170)
        self.download_plist.activated.connect(self.on_download_plist_activated)
        ingest_row.addWidget(self.download_plist)
        self.refresh_download_plist_combo()

        self.extract = QPushButton("다운로드")
        self.extract.setObjectName("primary")
        self.extract.clicked.connect(self.on_extract)
        ingest_row.addWidget(self.extract)

        self.mini_btn = QPushButton("미니")
        self.mini_btn.setCheckable(True)
        self.mini_btn.setToolTip("다운로드만 보이는 미니 모드 (링크 붙여넣기용)")
        self.mini_btn.toggled.connect(self.set_mini_mode)
        ingest_row.addWidget(self.mini_btn)

        # Progress
        self.status = QLabel("대기 중...")
        self.status.setStyleSheet("color:#aaaaaa; font-size:12px;")
        outer.addWidget(self.status)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        outer.addWidget(self.progress)

        self.full_panel = QWidget()
        full_layout = QVBoxLayout(self.full_panel)
        full_layout.setContentsMargins(0, 0, 0, 0)
        full_layout.setSpacing(12)

        # Main Splitter
        splitter = QSplitter(Qt.Horizontal)
        full_layout.addWidget(splitter, 1)

        # Left: Playlists
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0,0,0,0)
        
        plist_label = QLabel("플레이리스트")
        plist_label.setStyleSheet("font-weight:bold; font-size: 14px; color:#ffffff; margin-bottom: 4px;")
        left_layout.addWidget(plist_label)

        self.plist_widget = QListWidget()
        self.plist_widget.itemClicked.connect(self.on_playlist_clicked)
        self.plist_widget.setAcceptDrops(True)
        self.plist_widget.setDragDropMode(QAbstractItemView.DropOnly)
        self.plist_widget.viewport().installEventFilter(self)
        self.plist_widget.installEventFilter(self)
        left_layout.addWidget(self.plist_widget, 1)
        
        plist_btns = QHBoxLayout()
        self.btn_new_plist = QPushButton("+")
        self.btn_new_plist.setObjectName("icon_btn")
        self.btn_new_plist.setToolTip("새 플레이리스트 추가")
        self.btn_new_plist.setFixedWidth(30)
        self.btn_new_plist.clicked.connect(self.on_new_playlist)
        
        self.btn_del_plist = QPushButton("-")
        self.btn_del_plist.setObjectName("icon_btn")
        self.btn_del_plist.setToolTip("현재 플레이리스트 삭제")
        self.btn_del_plist.setFixedWidth(30)
        self.btn_del_plist.clicked.connect(self.on_del_playlist)
        plist_btns.addStretch()
        plist_btns.addWidget(self.btn_new_plist)
        plist_btns.addWidget(self.btn_del_plist)
        left_layout.addLayout(plist_btns)

        splitter.addWidget(left_widget)

        # Right: Table
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0,0,0,0)
        
        self.table = TrackTableWidget(self, 0, 4)
        self.table.setHorizontalHeaderLabels(["Track", "BPM", "Key", "Genre & Tags"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)  # Allow multi-select
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setDragEnabled(True)
        self.table.setDefaultDropAction(Qt.CopyAction)
        self.table.setDragDropMode(QTableWidget.DragOnly)
        self.table.setDropIndicatorShown(True)
        self.table.viewport().installEventFilter(self)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(50)
        self.table.setShowGrid(False)
        self.table.doubleClicked.connect(self.on_table_double_clicked)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.on_table_context_menu)

        # Action toolbar (library / selection actions) — sits above the table so
        # the bottom is reserved for the playback bar.
        actions_row = QHBoxLayout()
        actions_row.setSpacing(6)

        self.open_btn = QPushButton("폴더 열기")
        self.open_btn.clicked.connect(self.on_open_selected)
        actions_row.addWidget(self.open_btn)

        self.retag = QPushButton("태그 다중 편집")
        self.retag.clicked.connect(self.on_bulk_edit)
        actions_row.addWidget(self.retag)

        self.analyze_btn = QPushButton("상세정보 업데이트")
        self.analyze_btn.setToolTip(
            "BPM·Key가 Unknown인 곡: GetSongBPM DB 우선 → 실패 시 WAV 로컬 분석 (백그라운드)"
        )
        self.analyze_btn.clicked.connect(self.on_refresh_metadata)
        actions_row.addWidget(self.analyze_btn)

        self.add_to_plist_btn = QPushButton("+ 현재 곡 추가")
        self.add_to_plist_btn.clicked.connect(self.on_add_to_playlist)
        actions_row.addWidget(self.add_to_plist_btn)

        actions_row.addStretch(1)

        self.toggle_key_btn = QPushButton("Key 표기: 표준")
        self.toggle_key_btn.clicked.connect(self.toggle_key_notation)
        actions_row.addWidget(self.toggle_key_btn)

        self.delete_btn = QPushButton("삭제")
        self.delete_btn.setObjectName("danger")
        self.delete_btn.clicked.connect(self.on_delete_selected)
        actions_row.addWidget(self.delete_btn)

        right_layout.addLayout(actions_row)
        right_layout.addWidget(self.table, 1)

        splitter.addWidget(right_widget)
        splitter.setSizes([200, 1000])
        self.main_splitter = splitter
        splitter.splitterMoved.connect(self._on_main_splitter_moved)

        # Bottom player dock: [large cover | transport + info + waveform | mix]
        self._np_rec: dict | None = None
        self._cover_size = 180

        self.player_panel = QWidget()
        self.player_panel.setObjectName("playerPanel")
        self.player_panel.setMinimumHeight(128)
        player_bar = QHBoxLayout(self.player_panel)
        player_bar.setSpacing(14)
        player_bar.setContentsMargins(0, 8, 0, 4)

        # Left — album cover only (title/artist sit beside transport below)
        self.art_panel = QWidget()
        self.art_panel.setObjectName("ipodPanel")
        art_lay = QHBoxLayout(self.art_panel)
        art_lay.setSpacing(0)
        art_lay.setContentsMargins(0, 0, 4, 0)

        self.np_cover = QLabel()
        self.np_cover.setObjectName("ipodCover")
        self.np_cover.setAlignment(Qt.AlignCenter)
        self.np_cover.setFixedSize(120, 120)
        art_lay.addWidget(self.np_cover, 0, Qt.AlignVCenter)

        self.meta_panel = QWidget()
        self.meta_panel.setObjectName("npMeta")
        self.meta_panel.setFixedWidth(148)
        meta_lay = QVBoxLayout(self.meta_panel)
        meta_lay.setContentsMargins(0, 0, 6, 0)
        meta_lay.setSpacing(2)
        meta_lay.setAlignment(Qt.AlignVCenter)

        self.np_title = QLabel("")
        self.np_title.setObjectName("npTitle")
        self.np_title.setWordWrap(False)
        self.np_title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.np_title.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.np_title.setMinimumWidth(0)
        self.np_artist = QLabel("")
        self.np_artist.setObjectName("npArtist")
        self.np_artist.setWordWrap(False)
        self.np_artist.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.np_artist.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.np_artist.setMinimumWidth(0)
        meta_lay.addWidget(self.np_title)
        meta_lay.addWidget(self.np_artist)
        self.meta_panel.installEventFilter(self)

        self._np_title_text = ""
        self._np_artist_text = ""

        player_bar.addWidget(self.art_panel)

        # Center — waveform (Ctrl+wheel zoom) + transport row
        center_wrap = QWidget()
        center_wrap.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        center = QVBoxLayout(center_wrap)
        center.setContentsMargins(0, 0, 0, 0)
        center.setSpacing(6)

        self.wave_scroll = QScrollArea()
        self.wave_scroll.setWidgetResizable(False)
        self.wave_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.wave_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.wave_scroll.setFrameShape(QScrollArea.NoFrame)
        self.wave_scroll.setMinimumHeight(104)

        self.waveform_widget = WaveformWidget()
        self.waveform_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.waveform_widget.set_editable_cues(True)
        self.waveform_widget.setToolTip(
            "Ctrl+휠: 확대/축소 · Cue 마커 드래그 · +/− 로 Cue 추가/삭제"
        )
        self.waveform_widget.position_changed.connect(self.on_waveform_seek)
        self.waveform_widget.cues_changed.connect(self.on_waveform_cues_changed)
        self.wave_scroll.setWidget(self.waveform_widget)
        center.addWidget(self.wave_scroll, 1)

        controls_strip = QWidget()
        controls_strip.setObjectName("playerControlsStrip")
        strip_lay = QHBoxLayout(controls_strip)
        strip_lay.setContentsMargins(0, 2, 0, 0)
        strip_lay.setSpacing(0)

        strip_lay.addWidget(self.meta_panel, 0, Qt.AlignVCenter)

        transport_host = QWidget()
        transport_host.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        th_lay = QHBoxLayout(transport_host)
        th_lay.setContentsMargins(0, 0, 0, 0)
        th_lay.setSpacing(0)
        th_lay.addStretch(1)

        self.transport = IPodTransportBar()
        self.prev_btn = self.transport.prev_btn
        self.play_pause_btn = self.transport.play_btn
        self.next_btn = self.transport.next_btn
        self.prev_btn.setToolTip("이전 곡")
        self.play_pause_btn.setToolTip("재생 / 일시정지 (Space)")
        self.next_btn.setToolTip("다음 곡")
        self.prev_btn.clicked.connect(self.on_prev)
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        self.next_btn.clicked.connect(self.on_next)
        th_lay.addWidget(self.transport, 0, Qt.AlignCenter)
        th_lay.addStretch(1)
        strip_lay.addWidget(transport_host, 1)

        cue_tools = QWidget()
        cue_tools.setFixedWidth(148)
        cue_lay = QHBoxLayout(cue_tools)
        cue_lay.setContentsMargins(0, 0, 0, 0)
        cue_lay.setSpacing(8)
        cue_lay.addStretch(1)
        self.cue_add_btn = QPushButton("+")
        self.cue_add_btn.setObjectName("icon_btn")
        self.cue_add_btn.setFixedSize(36, 36)
        self.cue_add_btn.setToolTip("현재 위치에 Cue 포인트 추가 (IN → OUT)")
        self.cue_add_btn.clicked.connect(self.on_cue_add)
        cue_lay.addWidget(self.cue_add_btn)
        self.cue_del_btn = QPushButton("−")
        self.cue_del_btn.setObjectName("icon_btn")
        self.cue_del_btn.setFixedSize(36, 36)
        self.cue_del_btn.setToolTip("Cue 포인트 삭제 (OUT → IN)")
        self.cue_del_btn.clicked.connect(self.on_cue_delete)
        cue_lay.addWidget(self.cue_del_btn)
        strip_lay.addWidget(cue_tools, 0, Qt.AlignVCenter)

        center.addWidget(controls_strip, 0)

        player_bar.addWidget(center_wrap, 1)

        # Right — auto-mix (fixed width; hides nothing on narrow windows)
        mix = QVBoxLayout()
        mix.setSpacing(6)
        mix.setAlignment(Qt.AlignVCenter)

        self.autoplay_chk = QCheckBox("자동재생")
        self.autoplay_chk.setChecked(self.autoplay_enabled)
        self.autoplay_chk.setToolTip("곡이 끝나면 다음 곡을 자동으로 재생")
        self.autoplay_chk.toggled.connect(self.on_autoplay_toggled)
        mix.addWidget(self.autoplay_chk)

        self.crossfade_chk = QCheckBox("크로스페이드")
        self.crossfade_chk.setChecked(self.crossfade_enabled)
        self.crossfade_chk.setToolTip("곡 전환 시 볼륨을 부드럽게 겹쳐서 재생")
        self.crossfade_chk.toggled.connect(self.on_crossfade_toggled)
        mix.addWidget(self.crossfade_chk)

        xf_row = QHBoxLayout()
        xf_row.setSpacing(8)
        self.crossfade_slider = QSlider(Qt.Horizontal)
        self.crossfade_slider.setMinimum(1)
        self.crossfade_slider.setMaximum(12)
        self.crossfade_slider.setValue(self.crossfade_ms // 1000)
        self.crossfade_slider.setMinimumWidth(72)
        self.crossfade_slider.setMaximumWidth(120)
        self.crossfade_slider.setToolTip("크로스페이드 길이(초)")
        self.crossfade_slider.valueChanged.connect(self.on_crossfade_len_changed)
        xf_row.addWidget(self.crossfade_slider)

        self.crossfade_label = QLabel(f"{self.crossfade_ms // 1000}s")
        self.crossfade_label.setObjectName("npArtist")
        xf_row.addWidget(self.crossfade_label)
        mix.addLayout(xf_row)

        mix_wrap = QWidget()
        mix_wrap.setLayout(mix)
        mix_wrap.setFixedWidth(148)
        player_bar.addWidget(mix_wrap)

        full_layout.addWidget(self.player_panel)
        outer.addWidget(self.full_panel, 1)

        # Keep the play/pause icon synced with the actual playback state.
        for p in (self.player_a, self.player_b):
            p.playbackStateChanged.connect(self._sync_play_icon)

        self.update_now_playing(None)  # initial placeholder cover/labels
        QTimer.singleShot(0, self._sync_art_panel_width)
        QTimer.singleShot(50, self._refresh_now_playing_cover)
        self.refresh_playlists()
        self.render_table()

    def init_tray(self) -> None:
        self.tray = QSystemTrayIcon(self)
        if os.path.exists(self.icon_path):
            self.tray.setIcon(QIcon(self.icon_path))
        self.tray.setToolTip("WaveMash")
        self._rebuild_tray_menu()
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()

    def _rebuild_tray_menu(self) -> None:
        menu = QMenu(self)
        _style_context_menu(menu)

        open_action = menu.addAction("열기")
        open_action.triggered.connect(self.show_from_tray)

        mode_label = "전체 모드" if self.mini_mode else "미니 모드"
        mode_action = menu.addAction(mode_label)
        mode_action.triggered.connect(self.toggle_mini_mode_from_tray)

        update_action = menu.addAction("Unknown BPM/Key 업데이트")
        update_action.triggered.connect(lambda: self.on_refresh_metadata(quiet=True))

        menu.addSeparator()

        quit_action = menu.addAction("종료")
        quit_action.triggered.connect(self.force_quit)

        self.tray.setContextMenu(menu)

    def show_from_tray(self) -> None:
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def toggle_mini_mode_from_tray(self) -> None:
        self.set_mini_mode(not self.mini_mode)

    def set_mini_mode(self, enabled: bool) -> None:
        if self.mini_mode == enabled:
            if self.mini_btn.isChecked() != enabled:
                self.mini_btn.blockSignals(True)
                self.mini_btn.setChecked(enabled)
                self.mini_btn.blockSignals(False)
            return

        self.mini_mode = enabled
        self.mini_btn.blockSignals(True)
        self.mini_btn.setChecked(enabled)
        self.mini_btn.setText("전체" if enabled else "미니")
        self.mini_btn.blockSignals(False)
        self.full_panel.setVisible(not enabled)
        self.mini_drag.setVisible(enabled)
        if enabled and not self.mini_drag._paths and self.records:
            for rec in reversed(self.records):
                path = str(rec.get("path") or "")
                if path and os.path.isfile(path):
                    self.mini_drag.set_records([rec])
                    break

        if enabled:
            self._saved_geometry = self.geometry()
            self.setMinimumSize(480, 112)
            self.setMaximumHeight(168)
            self.resize(max(520, self.width()), 132)
            self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
            self.show()
        else:
            self.setMinimumSize(800, 600)
            self.setMaximumHeight(16777215)
            self.setWindowFlag(Qt.WindowStaysOnTopHint, False)
            if self._saved_geometry is not None:
                self.setGeometry(self._saved_geometry)
            else:
                self.resize(1200, 750)
            self.show()

        self._rebuild_tray_menu()

    def force_quit(self) -> None:
        QApplication.quit()

    def on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_from_tray()

    def closeEvent(self, event) -> None:
        event.ignore()
        self.hide()
        self.tray.showMessage(
            "WaveMash",
            "트레이에서 계속 실행됩니다. 미니 모드는 트레이 메뉴에서 전환할 수 있습니다.",
            QSystemTrayIcon.Information,
            2500,
        )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        QTimer.singleShot(0, self._refresh_now_playing_cover)
        wf = getattr(self, "waveform_widget", None)
        if wf is not None:
            QTimer.singleShot(0, wf._update_zoom_geometry)
        QTimer.singleShot(0, self._elide_np_labels)

    def _on_main_splitter_moved(self, pos: int, index: int) -> None:
        self._sync_art_panel_width()
        self._refresh_now_playing_cover()

    def _sync_art_panel_width(self) -> None:
        panel = getattr(self, "art_panel", None)
        if panel is None:
            return
        cover = self._art_cover_side()
        panel.setFixedWidth(cover + 4)
        QTimer.singleShot(0, self._elide_np_labels)

    def _art_cover_side(self) -> int:
        panel = getattr(self, "player_panel", None)
        h = panel.height() if panel else 128
        side = max(96, min(h - 16, 140))
        cover = getattr(self, "np_cover", None)
        if cover is not None:
            cover.setFixedSize(side, side)
        return side

    def _refresh_now_playing_cover(self) -> None:
        side = self._art_cover_side()
        if side > 40:
            self._cover_size = side
            self.update_now_playing(self._np_rec)

    # Playlist Management
    NO_PLAYLIST_LABEL = "(플리에 추가 안 함)"
    NEW_PLAYLIST_LABEL = "+ 새 플레이리스트…"

    def refresh_playlists(self) -> None:
        self.plist_widget.clear()
        self.plist_widget.addItem("All Tracks")
        for p in self.playlists:
            self.plist_widget.addItem(p)
            
        # Select current
        items = self.plist_widget.findItems(self.current_playlist, Qt.MatchExactly)
        if items:
            self.plist_widget.setCurrentItem(items[0])

        self.refresh_download_plist_combo()

    def refresh_download_plist_combo(self) -> None:
        """Keep the 'download into playlist' selector in sync with the playlists."""
        combo = getattr(self, "download_plist", None)
        if combo is None:
            return
        prev = combo.currentText() if combo.count() else self.NO_PLAYLIST_LABEL
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(self.NO_PLAYLIST_LABEL)
        for name in self.playlists:
            combo.addItem(name)
        combo.addItem(self.NEW_PLAYLIST_LABEL)
        idx = combo.findText(prev)
        combo.setCurrentIndex(idx if idx >= 0 else 0)
        combo.blockSignals(False)

    def on_download_plist_activated(self, index: int) -> None:
        if self.download_plist.currentText() != self.NEW_PLAYLIST_LABEL:
            return
        from PySide6.QtWidgets import QInputDialog

        text, ok = QInputDialog.getText(self, "새 플레이리스트", "플레이리스트 이름:")
        text = (text or "").strip()
        if ok and text and text != "All Tracks" and text not in self.playlists:
            self.playlists[text] = []
            self.save_playlists()
            self.refresh_playlists()  # also refreshes this combo
            i = self.download_plist.findText(text)
            if i >= 0:
                self.download_plist.setCurrentIndex(i)
        else:
            self.download_plist.setCurrentIndex(0)

    def selected_download_playlist(self) -> str | None:
        """The playlist chosen for new downloads, or None for no auto-add."""
        combo = getattr(self, "download_plist", None)
        if combo is None:
            return None
        name = combo.currentText()
        if name in (self.NO_PLAYLIST_LABEL, self.NEW_PLAYLIST_LABEL):
            return None
        return name if name in self.playlists else None

    def on_playlist_clicked(self, item) -> None:
        self.current_playlist = item.text()
        self.render_table()

    def on_new_playlist(self) -> None:
        # simple input dialog
        from PySide6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, "새 플레이리스트", "플레이리스트 이름:")
        if ok and text and text != "All Tracks" and text not in self.playlists:
            self.playlists[text] = []
            self.save_playlists()
            self.refresh_playlists()

    def on_del_playlist(self) -> None:
        if self.current_playlist == "All Tracks":
            return
        del self.playlists[self.current_playlist]
        self.save_playlists()
        self.current_playlist = "All Tracks"
        self.refresh_playlists()
        self.render_table()
        
    def on_add_to_playlist(self) -> None:
        if not hasattr(self, "current_playing_record") or not self.current_playing_record:
            QMessageBox.warning(self, "WaveMash", "현재 재생 중인 곡이 없습니다.")
            return
        if self.current_playlist == "All Tracks":
            QMessageBox.warning(self, "WaveMash", "왼쪽에서 현재 곡을 저장할 플레이리스트를 먼저 선택(클릭)해 주세요.")
            return
            
        rec_id = self.current_playing_record.get("id")
        if rec_id and rec_id not in self.playlists[self.current_playlist]:
            self.playlists[self.current_playlist].append(rec_id)
            self.save_playlists()
            QMessageBox.information(self, "WaveMash", f"현재 재생 중인 곡을 '{self.current_playlist}' 에 추가했습니다.")
        else:
            QMessageBox.information(self, "WaveMash", "이미 플레이리스트에 있는 곡입니다.")

    def get_display_records(self) -> list[dict[str, Any]]:
        """Records in the order currently shown in the table.

        For a real playlist this honors the stored (re-orderable) order; for
        'All Tracks' it is the raw archive order. Shared by render_table and
        the playback queue so the queue matches what the user sees.
        """
        if self.current_playlist != "All Tracks" and self.current_playlist in self.playlists:
            id_to_rec = {str(r.get("id", "")): r for r in self.records}
            return [
                id_to_rec[str(i)]
                for i in self.playlists[self.current_playlist]
                if str(i) in id_to_rec
            ]
        return list(self.records)

    def render_table(self) -> None:
        self.table.setRowCount(0)

        is_playlist_view = (
            self.current_playlist != "All Tracks"
            and self.current_playlist in self.playlists
        )
        display_records = self.get_display_records()

        # Allow drag-to-reorder only inside a real playlist
        if is_playlist_view:
            self.table.setDragDropMode(QTableWidget.DragDrop)
        else:
            self.table.setDragDropMode(QTableWidget.DragOnly)

        for rec in display_records:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Invisible item for sorting and holding UserRole ID
            id_item = QTableWidgetItem()
            id_item.setData(Qt.UserRole, str(rec.get("id", "")))
            self.table.setItem(row, 0, id_item)
            
            # Track widget (Cover + Title + Artist)
            wav_path = str(rec.get("path", ""))
            title = str(rec.get("title", ""))
            artist = str(rec.get("artist", ""))
            track_widget = TrackWidget(wav_path, title, artist)
            self.table.setCellWidget(row, 0, track_widget)
            
            bpm_item = QTableWidgetItem(str(rec.get("bpm", "")))
            bpm_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, bpm_item)
            
            # Key with colored badge
            raw_key = str(rec.get("key", ""))
            camelot_key = CAMELOT_WHEEL.get(raw_key, raw_key)
            display_key = camelot_key if self.show_camelot else raw_key
            
            key_widget = QWidget()
            key_layout = QHBoxLayout(key_widget)
            key_layout.setContentsMargins(0, 0, 0, 0)
            key_layout.setAlignment(Qt.AlignCenter)
            
            key_label = QLabel(display_key)
            if camelot_key in CAMELOT_COLORS:
                hex_color = CAMELOT_COLORS[camelot_key]
                if self.show_camelot:
                    # Camelot mode: Solid background badge with black text
                    key_label.setStyleSheet(f"background-color: {hex_color}; color: black; font-weight: bold; padding: 2px 6px; border-radius: 3px; font-size: 11px;")
                else:
                    # Standard mode: Just colored text
                    key_label.setStyleSheet(f"color: {hex_color}; font-weight: bold; background: transparent; padding: 4px;")
            else:
                key_label.setStyleSheet("color: white; font-weight: bold;")
                
            key_layout.addWidget(key_label)
            key_widget.setAttribute(Qt.WA_TransparentForMouseEvents)
            self.table.setCellWidget(row, 2, key_widget)
            
            # Genre & Tags
            genre_str = str(rec.get("genre", ""))
            tags_list = rec.get("tags", [])
            if not isinstance(tags_list, list):
                tags_list = []
            genre_widget = GenreTagsWidget(genre_str, tags_list)
            self.table.setCellWidget(row, 3, genre_widget)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)      # Track
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents) # BPM
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents) # Key
        header.setSectionResizeMode(3, QHeaderView.Stretch) # Genre & Tags

    def selected_records(self) -> list[dict[str, Any]]:
        rows = self.table.selectionModel().selectedRows()
        recs = []
        id_to_rec = {str(x.get("id", "")): x for x in self.records}
        for idx in rows:
            item = self.table.item(idx.row(), 0)
            rec_id = item.data(Qt.UserRole) if item else None
            rec = id_to_rec.get(str(rec_id or ""))
            if rec:
                recs.append(rec)
        return recs

    def selected_file_paths(self) -> list[str]:
        paths: list[str] = []
        seen: set[str] = set()
        for rec in self.selected_records():
            path = os.path.normpath(str(rec.get("path", "")))
            if path and os.path.isfile(path) and path not in seen:
                seen.add(path)
                paths.append(path)
        return paths

    def copy_selected_files_to_clipboard(self) -> bool:
        urls = [QUrl.fromLocalFile(p) for p in self.selected_file_paths()]
        if not urls:
            return False
        mime = QMimeData()
        mime.setUrls(urls)
        QApplication.clipboard().setMimeData(mime, QClipboard.Clipboard)
        count = len(urls)
        self.status.setText(
            f"파일 {count}개 복사됨 — Explorer/Ableton/폴더에서 Ctrl+V"
            if count > 1
            else "파일 복사됨 — Explorer/Ableton/폴더에서 Ctrl+V"
        )
        return True

    def _should_handle_track_copy(self) -> bool:
        if isinstance(QApplication.focusWidget(), QLineEdit):
            return False
        return bool(self.selected_file_paths())

    def toggle_key_notation(self) -> None:
        self.show_camelot = not self.show_camelot
        self.toggle_key_btn.setText("Key 표기: 카멜롯" if self.show_camelot else "Key 표기: 표준")
        self.render_table()

    def set_busy(self, busy: bool) -> None:
        self.extract.setEnabled(not busy)
        self.url.setEnabled(not busy)
        self.yt_search_btn.setEnabled(not busy)

    @staticmethod
    def _looks_like_download_url(text: str) -> bool:
        t = text.strip().lower()
        if not t:
            return False
        if t.startswith("http://") or t.startswith("https://"):
            return True
        return any(
            token in t
            for token in (
                "youtube.com",
                "youtu.be",
                "soundcloud.com",
                "spotify.com",
            )
        )

    def _detect_source(self, url: str) -> str | None:
        lower = url.lower()
        if "spotify.com" in lower:
            return "spotify"
        if "youtube.com" in lower or "youtu.be" in lower or "soundcloud.com" in lower:
            return "stream"
        return None

    def on_youtube_search(self) -> None:
        query = self.url.text().strip()
        dlg = VersionFinderDialog(self.pool, query, self)
        if dlg.exec() != QDialog.Accepted or not dlg.selected:
            return
        if len(dlg.selected) == 1:
            self.url.setText(str(dlg.selected[0].get("url", "")))
        self._start_downloads_from_candidates(dlg.selected)

    def _start_downloads_from_candidates(
        self,
        candidates: list[dict[str, Any]],
        *,
        group_key: str | None = None,
    ) -> None:
        items: list[tuple[str, str]] = []
        for cand in candidates:
            url = str(cand.get("url") or "")
            if url:
                items.append(("stream", url))
        if not items:
            return
        if group_key:
            self._pending_version_group = group_key
        else:
            self._pending_version_group = None
        self._download_target_playlist = self.selected_download_playlist()
        self._download_queue.extend(items)
        self._pump_download_queue()

    def _pump_download_queue(self) -> None:
        if self._download_active or not self._download_queue:
            return
        source, url = self._download_queue.pop(0)
        self._download_active = True
        self.set_busy(True)
        self.progress.setValue(0)
        target = self._download_target_playlist
        self.status.setText(
            f"다운로드 중... ({len(self._download_queue) + 1}개 남음) → '{target}'"
            if self._download_queue and target
            else f"다운로드 중... → '{target}'" if target else "다운로드 중..."
        )
        job = self.pool.start_download(JobRequest(source=source, url=url))
        job.signals.progress.connect(self.on_progress)
        job.signals.finished.connect(self._on_queued_download_finished)
        job.signals.failed.connect(self._on_queued_download_failed)

    def _on_queued_download_finished(self, result: object) -> None:
        group_key = getattr(self, "_pending_version_group", None)
        if group_key:
            self.on_version_downloaded(result, group_key)
        else:
            self.on_finished(result)
        self._download_active = False
        if self._download_queue:
            self._pump_download_queue()
        else:
            self._pending_version_group = None
            self.set_busy(False)
            if self.mini_mode:
                self.url.setFocus()

    def _on_queued_download_failed(self, error: str) -> None:
        self.on_failed(error)
        self._download_active = False
        if self._download_queue:
            self._pump_download_queue()
        else:
            self._pending_version_group = None

    def on_extract(self) -> None:
        text = self.url.text().strip()
        if not text:
            QMessageBox.warning(self, "WaveMash", "URL 또는 검색어를 입력해 주세요.")
            return

        if not self._looks_like_download_url(text):
            dlg = VersionFinderDialog(self.pool, text, self)
            if dlg.exec() != QDialog.Accepted or not dlg.selected:
                return
            if len(dlg.selected) == 1:
                self.url.setText(str(dlg.selected[0].get("url", "")))
            self._start_downloads_from_candidates(dlg.selected)
            return

        source = self._detect_source(text)
        if source is None:
            QMessageBox.warning(
                self,
                "WaveMash",
                "지원하지 않는 URL입니다. (YouTube, SoundCloud, Spotify)",
            )
            return

        self._download_target_playlist = self.selected_download_playlist()
        self._download_queue = [(source, text)]
        self._pending_version_group = None
        self._pump_download_queue()

    def on_progress(self, p: float, message: str) -> None:
        self.progress.setValue(int(max(0.0, min(1.0, p)) * 100))
        self.status.setText(message)

    def on_finished(self, result: object) -> None:
        skipped = 0
        already_have = False
        if isinstance(result, dict):
            if 'records' in result or 'already_have' in result or 'downloaded' in result:
                skipped = int(result.get('skipped') or 0)
                already_have = bool(result.get('already_have'))
                records = list(result.get('records') or [])
            elif result.get('path') or result.get('id'):
                records = [result]
            else:
                records = []
        elif isinstance(result, list):
            records = result
        else:
            records = [result] if result else []

        saved = 0
        title_last = ""
        saved_ids: list[str] = []
        saved_recs: list[dict[str, Any]] = []
        for rec in records:
            if not isinstance(rec, dict):
                continue
            rid = str(rec.get("id", ""))
            path = str(rec.get("path", ""))
            if already_have:
                if rid:
                    saved_ids.append(rid)
                    title_last = rec.get("title", title_last)
                    if path and os.path.isfile(path):
                        saved_recs.append(dict(rec))
                continue
            if path and os.path.isfile(path):
                self.records = upsert_record(self.records, dict(rec))
                saved += 1
                title_last = rec.get("title", "")
                if rid:
                    saved_ids.append(rid)
                saved_recs.append(dict(rec))

        # Auto-add the new tracks to the playlist chosen before downloading.
        target = getattr(self, "_download_target_playlist", None)
        added = 0
        if target and target in self.playlists and saved_ids:
            for rid in saved_ids:
                if rid not in self.playlists[target]:
                    self.playlists[target].append(rid)
                    added += 1
            if added:
                self.save_playlists()
        self._download_target_playlist = None

        if saved_recs:
            self.mini_drag.set_records(saved_recs)

        self.render_table()
        if already_have:
            if target and added:
                self.status.setText(
                    f"이미 보유 중 ({skipped}곡) · '{target}' 플레이리스트에 {added}곡 추가"
                )
            elif skipped == 1 and title_last:
                self.status.setText(f"이미 라이브러리에 있습니다: {title_last}")
            else:
                self.status.setText(f"이미 보유 중 ({skipped}곡 스킵)")
            self.tray.showMessage(
                "WaveMash",
                title_last or f"이미 보유 중 ({skipped}곡)",
                QSystemTrayIcon.Information,
                3000,
            )
        elif saved == 0:
            self.status.setText("다운로드했지만 저장된 파일이 없습니다.")
            self.tray.showMessage("WaveMash", "저장된 파일이 없습니다.", QSystemTrayIcon.Warning, 3000)
        elif target and added:
            self.status.setText(f"완료! ({saved}개 저장 · {skipped}곡 스킵 · '{target}'에 {added}곡 추가)")
        elif skipped:
            self.status.setText(f"완료! ({saved}개 저장 · {skipped}곡 스킵)")
        else:
            self.status.setText(f"완료! ({saved}개 저장)")
            self.tray.showMessage(
                "WaveMash",
                f"다운로드 완료: {title_last} 외 {saved-1}개" if saved > 1 else f"다운로드 완료: {title_last}",
                QSystemTrayIcon.Information,
                3000,
            )
        self.progress.setValue(100)
        if not self._download_queue and not self._download_active:
            self.set_busy(False)
        self.url.setText("")
        if self.mini_mode:
            self.url.setFocus()

    def on_failed(self, error: str) -> None:
        self.status.setText(f"실패: {error}")
        self.progress.setValue(0)
        if not self._download_queue and not self._download_active:
            self.set_busy(False)
        self.tray.showMessage("WaveMash 실패", error, QSystemTrayIcon.Warning, 3000)

    def on_open_selected(self) -> None:
        recs = self.selected_records()
        if not recs:
            QMessageBox.warning(self, "WaveMash", "먼저 곡을 선택해 주세요.")
            return
        _open_in_explorer(str(recs[0].get("path", "")))

    # ---- Deck helpers -------------------------------------------------
    def _player(self, deck: str) -> QMediaPlayer:
        return self.player_a if deck == "a" else self.player_b

    def _output(self, deck: str) -> QAudioOutput:
        return self.audio_output_a if deck == "a" else self.audio_output_b

    def cur_player(self) -> QMediaPlayer:
        return self._player(self.cur)

    def other_deck(self) -> str:
        return "b" if self.cur == "a" else "a"

    # ---- Queue / playback --------------------------------------------
    def on_play_selected(self) -> None:
        recs = self.selected_records()
        if not recs:
            return
        # Build the play queue from the current view so auto-advance follows it
        self.play_queue = self.get_display_records()
        target_id = str(recs[0].get("id", ""))
        index = next(
            (i for i, r in enumerate(self.play_queue) if str(r.get("id", "")) == target_id),
            -1,
        )
        if index < 0:
            # Selection not in the current view; play it as a one-item queue
            self.play_queue = [recs[0]]
            index = 0
        self.goto_index(index, use_crossfade=False)

    def play_track_on_current_deck(self, rec: dict) -> None:
        """Hard-cut: stop any fade, play `rec` on the foreground deck."""
        self._cancel_fade()
        self._player(self.other_deck()).stop()
        path = str(rec.get("path", ""))
        if not os.path.isfile(path):
            return
        self.current_playing_record = rec
        self.update_now_playing(rec)
        self._pending_seek = None
        self._output(self.cur).setVolume(1.0)
        self.waveform_widget.load_audio(path)
        self.waveform_widget.set_analysis(rec.get("analysis"))
        player = self.cur_player()
        player.setSource(QUrl.fromLocalFile(path))
        player.play()

    def goto_index(self, index: int, use_crossfade: bool = True) -> bool:
        if index < 0 or index >= len(self.play_queue):
            return False
        rec = self.play_queue[index]
        path = str(rec.get("path", ""))
        if not os.path.isfile(path):
            return False

        already_playing = self.cur_player().playbackState() == QMediaPlayer.PlayingState
        if use_crossfade and self.crossfade_enabled and already_playing and not self.fading:
            self.start_crossfade(rec)
        else:
            self.play_track_on_current_deck(rec)
        self.queue_index = index
        return True

    def _ensure_queue(self) -> None:
        if not self.play_queue:
            self.play_queue = self.get_display_records()
            self.queue_index = -1

    def on_next(self) -> None:
        self._ensure_queue()
        self.goto_index(self.queue_index + 1, use_crossfade=self.crossfade_enabled)

    def on_prev(self) -> None:
        self._ensure_queue()
        # Previous always hard-cuts (more predictable when skipping back)
        self.goto_index(max(0, self.queue_index - 1), use_crossfade=False)

    # ---- Crossfade ----------------------------------------------------
    def start_crossfade(self, rec: dict) -> None:
        path = str(rec.get("path", ""))
        if not os.path.isfile(path):
            return

        out_deck = self.cur
        in_deck = self.other_deck()

        in_player = self._player(in_deck)
        self._output(in_deck).setVolume(0.0)
        in_player.setSource(QUrl.fromLocalFile(path))
        in_player.play()

        # Start the incoming track at its mix-in cue (skip dead-air intro) so the
        # blend keeps energy up. Applied once the media reports as loaded.
        analysis = rec.get("analysis")
        cue_in = analysis.get("cue_in") if isinstance(analysis, dict) else None
        if cue_in and cue_in > 1.0:
            self._pending_seek = (in_deck, int(cue_in * 1000))
        else:
            self._pending_seek = None

        # The incoming track becomes the "now playing" foreground immediately
        self.cur = in_deck
        self.current_playing_record = rec
        self.update_now_playing(rec)
        self.waveform_widget.load_audio(path)
        self.waveform_widget.set_analysis(analysis)

        self._fade_out_deck = out_deck
        self._fade_in_deck = in_deck
        self._fade_elapsed = 0
        self.fading = True
        self.fade_timer.start()

    def _on_fade_tick(self) -> None:
        if not self.fading or self._fade_out_deck is None or self._fade_in_deck is None:
            self._cancel_fade()
            return

        self._fade_elapsed += self.fade_timer.interval()
        t = min(1.0, self._fade_elapsed / max(1, self.crossfade_ms))

        # Equal-power crossfade curve keeps perceived loudness roughly constant
        out_vol = math.cos(t * math.pi / 2)
        in_vol = math.sin(t * math.pi / 2)
        self._output(self._fade_out_deck).setVolume(out_vol)
        self._output(self._fade_in_deck).setVolume(in_vol)

        if t >= 1.0:
            self._finish_fade()

    def _finish_fade(self) -> None:
        if self._fade_out_deck is not None:
            self._player(self._fade_out_deck).stop()
        if self._fade_in_deck is not None:
            self._output(self._fade_in_deck).setVolume(1.0)
        self.fade_timer.stop()
        self.fading = False
        self._fade_out_deck = None
        self._fade_in_deck = None

    def _cancel_fade(self) -> None:
        self.fade_timer.stop()
        self.fading = False
        self._fade_out_deck = None
        self._fade_in_deck = None

    # ---- Player signal handlers --------------------------------------
    def on_player_position_changed(self, position):
        player = self.sender()
        if player is not self.cur_player():
            return
        duration = player.duration()
        if duration > 0:
            self.waveform_widget.set_progress(position / duration)
            self.current_duration = duration

            # Trigger the crossfade at the track's mix-out cue (start of the
            # outro) when available, otherwise crossfade_ms before the end.
            trigger_ms = duration - self.crossfade_ms
            cur_rec = getattr(self, "current_playing_record", None)
            if cur_rec and isinstance(cur_rec.get("analysis"), dict):
                cue_out = cur_rec["analysis"].get("cue_out")
                if cue_out and 0 < cue_out * 1000 < duration:
                    trigger_ms = min(trigger_ms if trigger_ms > 0 else cue_out * 1000,
                                     cue_out * 1000)

            if (
                self.autoplay_enabled
                and self.crossfade_enabled
                and not self.fading
                and position >= trigger_ms
                and self.queue_index + 1 < len(self.play_queue)
            ):
                self.goto_index(self.queue_index + 1, use_crossfade=True)

    def on_player_duration_changed(self, duration):
        if self.sender() is self.cur_player():
            self.current_duration = duration

    def on_media_status_changed(self, status):
        player = self.sender()

        # Apply a queued mix-in seek once the incoming deck's media is ready
        if self._pending_seek is not None and status in (
            QMediaPlayer.LoadedMedia, QMediaPlayer.BufferedMedia
        ):
            deck, pos_ms = self._pending_seek
            if player is self._player(deck):
                player.setPosition(pos_ms)
                self._pending_seek = None

        if player is not self.cur_player() or self.fading:
            return
        if status == QMediaPlayer.EndOfMedia and self.autoplay_enabled:
            # Reached natural end without a crossfade (e.g. crossfade off or
            # track shorter than the fade window): hard-cut to the next track.
            self.goto_index(self.queue_index + 1, use_crossfade=False)

    def on_waveform_seek(self, pct: float):
        player = self.cur_player()
        duration = player.duration()
        if duration > 0:
            player.setPosition(int(duration * pct))

    def _now_playing_record(self) -> dict | None:
        rec = getattr(self, "current_playing_record", None)
        if rec and rec.get("path"):
            return rec
        sel = self.selected_records()
        return sel[0] if sel else None

    def on_cue_add(self) -> None:
        rec = self._now_playing_record()
        if not rec:
            QMessageBox.warning(self, "WaveMash", "재생 중이거나 선택한 곡이 없습니다.")
            return
        player = self.cur_player()
        duration = player.duration()
        if duration <= 0:
            QMessageBox.information(self, "WaveMash", "곡을 먼저 재생하세요.")
            return
        t = player.position() / 1000.0
        if not isinstance(rec.get("analysis"), dict):
            rec["analysis"] = {"duration": self.waveform_widget.track_duration}
        self.waveform_widget.add_cue_at(t)

    def on_cue_delete(self) -> None:
        rec = self._now_playing_record()
        if not rec:
            return
        if not self.waveform_widget.delete_cue():
            self.status.setText("삭제할 Cue 포인트가 없습니다.")

    def on_waveform_cues_changed(self) -> None:
        rec = self._now_playing_record()
        if not rec:
            return
        wf = self.waveform_widget
        analysis = dict(rec.get("analysis") or {})
        if wf.track_duration:
            analysis["duration"] = wf.track_duration
        for key, val in (("cue_in", wf.cue_in), ("cue_out", wf.cue_out)):
            if val is not None:
                analysis[key] = round(float(val), 3)
            else:
                analysis.pop(key, None)
        rid = str(rec.get("id", ""))
        for r in self.records:
            if str(r.get("id", "")) == rid:
                r["analysis"] = analysis
                break
        rec["analysis"] = analysis
        playing = getattr(self, "current_playing_record", None)
        if playing and str(playing.get("id", "")) == rid:
            playing["analysis"] = analysis
        save_archive(self.records)
        self.status.setText("Cue 저장됨")

    def toggle_play_pause(self):
        player = self.cur_player()
        state = player.playbackState()
        if state == QMediaPlayer.PlayingState:
            player.pause()
        elif state == QMediaPlayer.PausedState:
            player.play()
        else:
            # Nothing loaded yet: start from the selection, else the queue head.
            if self.selected_records():
                self.on_play_selected()
            else:
                self._ensure_queue()
                if self.play_queue:
                    self.goto_index(max(0, self.queue_index), use_crossfade=False)
        self._sync_play_icon()

    def _sync_play_icon(self, *args):
        btn = getattr(self, "play_pause_btn", None)
        if btn is None:
            return
        playing = self.cur_player().playbackState() == QMediaPlayer.PlayingState
        if hasattr(btn, "set_playing"):
            btn.set_playing(playing)

    # ---- Now Playing (cover + title/artist) --------------------------
    def _rounded_pixmap(self, src: QPixmap, size: int, radius: int = 10) -> QPixmap:
        """Center-cropped, rounded-corner cover at the requested size."""
        scaled = src.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        out = QPixmap(size, size)
        out.fill(Qt.transparent)
        painter = QPainter(out)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, size, size, radius, radius)
        painter.setClipPath(path)
        x = (scaled.width() - size) // 2
        y = (scaled.height() - size) // 2
        painter.drawPixmap(-x, -y, scaled)
        painter.end()
        return out

    def _placeholder_cover(self, size: int, radius: int = 10) -> QPixmap:
        out = QPixmap(size, size)
        out.fill(Qt.transparent)
        painter = QPainter(out)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, size, size, radius, radius)
        painter.fillPath(path, QColor("#2b2b2e"))
        painter.setPen(QColor("#5a5a5e"))
        f = painter.font()
        f.setPixelSize(int(size * 0.42))
        painter.setFont(f)
        painter.drawText(out.rect(), Qt.AlignCenter, "\u266a")
        painter.end()
        return out

    def _cover_pixmap_for(self, rec: dict | None, size: int) -> QPixmap:
        if rec:
            wav_path = str(rec.get("path", ""))
            pm = cover_pixmap_for_path(wav_path, size)
            if pm is not None and not pm.isNull():
                return self._rounded_pixmap(pm, size)
        return self._placeholder_cover(size)

    def _clean_artist_display(self, artist: str) -> str:
        """Fix common metadata glitches (e.g. 'Brad OberhoferOberhofer')."""
        artist = (artist or "").strip()
        parts = artist.split()
        if len(parts) >= 2:
            last = parts[-1]
            if len(last) >= 4 and len(last) % 2 == 0:
                half = len(last) // 2
                if last[:half].lower() == last[half:].lower():
                    parts[-1] = last[:half]
                    return " ".join(parts)
        return artist

    def _elide_np_labels(self) -> None:
        meta = getattr(self, "meta_panel", None)
        if meta is None:
            return
        width = self.np_title.width()
        if width <= 0:
            width = meta.width() - 4
        width = max(80, width)
        title = getattr(self, "_np_title_text", "")
        artist = getattr(self, "_np_artist_text", "")
        if title and self.np_title.isVisible():
            self.np_title.setText(
                QFontMetrics(self.np_title.font()).elidedText(title, Qt.ElideRight, width)
            )
        if artist and self.np_artist.isVisible():
            self.np_artist.setText(
                QFontMetrics(self.np_artist.font()).elidedText(artist, Qt.ElideRight, width)
            )

    def update_now_playing(self, rec: dict | None) -> None:
        self._np_rec = rec
        cover = getattr(self, "np_cover", None)
        if cover is None:
            return
        side = self._cover_size
        if cover.width() > 40:
            side = min(cover.width(), cover.height()) - 4
        cover.setPixmap(self._cover_pixmap_for(rec, side))
        if rec:
            self._np_title_text = str(rec.get("title", "")) or "Unknown"
            artist = self._clean_artist_display(str(rec.get("artist", "")))
            label = self._version_label(rec)
            if label and label != "Original":
                artist = f"{artist} · {label}" if artist else label
            self._np_artist_text = artist
            self.np_title.setVisible(True)
            self.np_artist.setVisible(bool(artist))
        else:
            self._np_title_text = ""
            self._np_artist_text = ""
            self.np_title.setVisible(False)
            self.np_artist.setVisible(False)
        QTimer.singleShot(0, self._elide_np_labels)

    # ---- Auto-mix settings handlers ----------------------------------
    def on_autoplay_toggled(self, checked: bool) -> None:
        self.autoplay_enabled = checked

    def on_crossfade_toggled(self, checked: bool) -> None:
        self.crossfade_enabled = checked

    def on_crossfade_len_changed(self, seconds: int) -> None:
        self.crossfade_ms = seconds * 1000
        self.crossfade_label.setText(f"{seconds}s")

    # ---- External BPM/Key lookup ------------------------------------
    def on_refresh_metadata(self, *, quiet: bool = False) -> None:
        if self._metadata_job is not None:
            msg = "상세정보 업데이트가 이미 진행 중입니다."
            if quiet:
                self.tray.showMessage("WaveMash", msg, QSystemTrayIcon.Information, 2500)
            else:
                self.status.setText(msg)
            return

        selected = self.selected_records()
        if selected:
            recs = [r for r in selected if needs_bpm_key_update(r)]
        else:
            recs = [r for r in self.records if needs_bpm_key_update(r)]

        tracks: list[tuple[str, str, str, str, str]] = []
        for r in recs:
            path = str(r.get("path", ""))
            if path and os.path.isfile(path):
                tracks.append((
                    str(r.get("id", "")),
                    str(r.get("artist", "")),
                    str(r.get("title", "")),
                    str(r.get("url", "")),
                    path,
                ))

        if not tracks:
            msg = "업데이트할 곡이 없습니다. (BPM·Key가 모두 채워져 있음)"
            if quiet:
                self.tray.showMessage("WaveMash", msg, QSystemTrayIcon.Information, 3000)
            else:
                QMessageBox.information(self, "WaveMash", msg)
            return

        self._metadata_refresh_total = len(tracks)
        self.status.setText(f"BPM/Key 조회 중... (0/{len(tracks)})")
        job = self.pool.start_metadata_refresh(tracks)
        self._metadata_job = job
        job.signals.progress.connect(self.on_metadata_progress)
        job.signals.one_done.connect(self.on_metadata_one_done)
        job.signals.finished.connect(self.on_metadata_finished)
        job.signals.failed.connect(self.on_metadata_failed)
        if quiet:
            self.tray.showMessage(
                "WaveMash",
                f"Unknown BPM/Key {len(tracks)}곡 업데이트 시작",
                QSystemTrayIcon.Information,
                2500,
            )

    def on_metadata_progress(self, p: float, message: str) -> None:
        self.progress.setValue(int(max(0.0, min(1.0, p)) * 100))
        self.status.setText(message)

    def on_metadata_failed(self, error: str) -> None:
        self._metadata_job = None
        self.status.setText(f"상세정보 업데이트 실패: {error}")
        self.tray.showMessage(
            "WaveMash",
            f"상세정보 업데이트 실패: {error}",
            QSystemTrayIcon.Warning,
            4000,
        )

    def on_metadata_one_done(self, track_id: str, payload: object) -> None:
        from library import apply_bpm_key_to_record

        rec = next((r for r in self.records if str(r.get("id")) == str(track_id)), None)
        if rec is None or not isinstance(payload, dict):
            return
        if apply_bpm_key_to_record(rec, payload.get("bpm"), payload.get("key")):
            cur = getattr(self, "current_playing_record", None)
            if cur and str(cur.get("id")) == str(track_id):
                self.update_now_playing(rec)

    def on_metadata_finished(self, count: int) -> None:
        self._metadata_job = None
        save_archive(self.records)
        total = getattr(self, "_metadata_refresh_total", 0)
        if count:
            msg = f"상세정보 업데이트 완료: {count}/{total}곡"
            self.status.setText(msg)
            icon = QSystemTrayIcon.Information
        else:
            msg = (
                "BPM/Key를 찾지 못했습니다. "
                "WAV 파일 경로를 확인하거나 .env에 GETSONGBPM_API_KEY를 설정해 보세요."
            )
            self.status.setText(msg)
            icon = QSystemTrayIcon.Warning
        self.progress.setValue(100)
        self.render_table()
        self.tray.showMessage("WaveMash", msg, icon, 4000)

    def on_covers_repaired(self, count: int) -> None:
        if count:
            self.render_table()
            playing = getattr(self, "current_playing_record", None)
            if playing:
                self.update_now_playing(playing)
            self.status.setText(f"앨범 커버 복구: {count}곡")

    def _is_internal_track_drag(self, event) -> bool:
        if event.source() is self.table:
            return True
        mime = event.mimeData()
        return bool(
            mime
            and mime.hasFormat(TrackTableWidget.INTERNAL_TRACK_MIME)
        )

    def _track_ids_from_drag(self, event) -> list[str]:
        mime = event.mimeData()
        if mime and mime.hasFormat(TrackTableWidget.INTERNAL_TRACK_MIME):
            raw = bytes(mime.data(TrackTableWidget.INTERNAL_TRACK_MIME)).decode("utf-8")
            return [part for part in raw.split(",") if part]
        return [str(r.get("id", "")) for r in self.selected_records() if r.get("id")]

    def _playlist_name_at(self, pos) -> str | None:
        item = self.plist_widget.itemAt(pos)
        if item:
            return item.text()
        for i in range(self.plist_widget.count()):
            it = self.plist_widget.item(i)
            if it and self.plist_widget.visualItemRect(it).contains(pos):
                return it.text()
        return None

    def _plist_drop_pos(self, obj, event):
        pos = event.position().toPoint()
        if obj is self.plist_widget:
            return self.plist_widget.viewport().mapFrom(self.plist_widget, pos)
        return pos

    def _handle_playlist_drop(self, event, pos) -> bool:
        if not self._is_internal_track_drag(event):
            return False
        event.acceptProposedAction()
        plist = self._playlist_name_at(pos)
        if plist and plist != "All Tracks":
            track_ids = self._track_ids_from_drag(event)
            self.add_track_ids_to_playlist(plist, track_ids)
        return True

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj is getattr(self, "meta_panel", None) and event.type() == QEvent.Resize:
            self._elide_np_labels()
        elif event.type() == QEvent.KeyPress and event.key() == Qt.Key_Space:
            focus_widget = QApplication.focusWidget()
            if not isinstance(focus_widget, QLineEdit):
                self.toggle_play_pause()
                return True
        elif event.type() == QEvent.KeyPress and event.key() == Qt.Key_Delete:
            focus_widget = QApplication.focusWidget()
            if isinstance(focus_widget, QLineEdit):
                return super().eventFilter(obj, event)
            if self.selected_records():
                self.on_delete_selected()
                return True
        elif (
            event.type() == QEvent.KeyPress
            and event.key() == Qt.Key_C
            and event.modifiers() & Qt.ControlModifier
            and self._should_handle_track_copy()
        ):
            self.copy_selected_files_to_clipboard()
            return True
                
        # Handle reordering inside the table when a playlist is selected
        table = getattr(self, "table", None)
        if table is not None and obj == table.viewport() and event.type() in (
            QEvent.DragEnter, QEvent.DragMove, QEvent.Drop
        ):
            if (
                event.source() == self.table
                and self.current_playlist != "All Tracks"
                and self.current_playlist in self.playlists
            ):
                if event.type() == QEvent.Drop:
                    event.acceptProposedAction()
                    self.reorder_current_playlist(event.position().toPoint())
                else:
                    event.acceptProposedAction()
                return True

        # Handle drop on playlist sidebar (DragMove must accept or Drop never fires)
        if obj in (self.plist_widget, self.plist_widget.viewport()):
            if event.type() in (QEvent.DragEnter, QEvent.DragMove):
                if self._is_internal_track_drag(event):
                    event.acceptProposedAction()
                    return True
            elif event.type() == QEvent.Drop:
                pos = self._plist_drop_pos(obj, event)
                if self._handle_playlist_drop(event, pos):
                    return True

        return super().eventFilter(obj, event)

    def reorder_current_playlist(self, drop_pos) -> None:
        plist = self.current_playlist
        if plist == "All Tracks" or plist not in self.playlists:
            return

        # Current on-screen order of track ids
        displayed_ids = [
            self.table.item(r, 0).data(Qt.UserRole)
            for r in range(self.table.rowCount())
        ]
        if not displayed_ids:
            return

        # Rows being moved (in their current visual order)
        sel_rows = sorted({idx.row() for idx in self.table.selectionModel().selectedRows()})
        moving = [displayed_ids[r] for r in sel_rows if 0 <= r < len(displayed_ids)]
        if not moving:
            return

        # Figure out where to insert (before the row we dropped onto)
        target_index = self.table.indexAt(drop_pos)
        target_row = target_index.row()
        insert_before = displayed_ids[target_row] if 0 <= target_row < len(displayed_ids) else None

        remaining = [i for i in displayed_ids if i not in moving]
        if insert_before is None or insert_before in moving or insert_before not in remaining:
            new_order = remaining + moving
        else:
            pos = remaining.index(insert_before)
            new_order = remaining[:pos] + moving + remaining[pos:]

        if new_order == displayed_ids:
            return  # nothing changed

        # Preserve any ids stored in the playlist that aren't currently shown
        orphans = [i for i in self.playlists[plist] if str(i) not in {str(x) for x in displayed_ids}]
        self.playlists[plist] = new_order + orphans
        self.save_playlists()
        self.render_table()

    def add_track_ids_to_playlist(self, plist: str, track_ids: list[str]) -> None:
        if not track_ids or plist not in self.playlists:
            return
        added = 0
        for rec_id in track_ids:
            if rec_id and rec_id not in self.playlists[plist]:
                self.playlists[plist].append(rec_id)
                added += 1
        self.save_playlists()
        if added > 0:
            QMessageBox.information(self, "WaveMash", f"{added}곡을 '{plist}' 에 추가했습니다.")
        else:
            QMessageBox.information(self, "WaveMash", "이미 플레이리스트에 있는 곡입니다.")

    def add_selected_to_playlist(self, plist: str) -> None:
        track_ids = [str(r.get("id", "")) for r in self.selected_records() if r.get("id")]
        self.add_track_ids_to_playlist(plist, track_ids)

    # ---- Versions (Original / Extended / Radio ...) -------------------
    _VERSION_ORDER = {
        "Original": 0, "Radio Edit": 1, "Short Edit": 2,
        "Club Mix": 3, "Extended": 4, "VIP": 5, "Instrumental": 6,
    }

    def _effective_group_key(self, rec: dict) -> str:
        """A track's version-group key: explicit link if set, else derived."""
        g = rec.get("version_group")
        if g:
            return str(g)
        return version_group_key(rec.get("artist", ""), rec.get("title", ""))

    def _version_label(self, rec: dict) -> str:
        return str(rec.get("version_label") or split_version(rec.get("title", ""))[1])

    def versions_of(self, rec: dict) -> list[dict]:
        """All records that are versions of the same recording, Original first."""
        key = self._effective_group_key(rec)
        members = [r for r in self.records if self._effective_group_key(r) == key]
        members.sort(key=lambda r: (self._VERSION_ORDER.get(self._version_label(r), 9),
                                     str(r.get("title", ""))))
        return members

    def on_table_context_menu(self, pos) -> None:
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        id_item = self.table.item(row, 0)
        if id_item is None:
            return
        rec_id = str(id_item.data(Qt.UserRole))
        rec = next((r for r in self.records if str(r.get("id", "")) == rec_id), None)
        if rec is None:
            return

        # Right-click selects the row unless it's already within a multi-selection.
        sel_rows = {idx.row() for idx in self.table.selectionModel().selectedRows()}
        if row not in sel_rows:
            self.table.selectRow(row)

        menu = QMenu(self)
        act_play = menu.addAction("재생")

        versions = self.versions_of(rec)
        if len(versions) > 1:
            vmenu = menu.addMenu(f"버전 전환  ({len(versions)})")
            for v in versions:
                mark = "● " if str(v.get("id", "")) == rec_id else "○ "
                a = vmenu.addAction(f"{mark}{self._version_label(v)} — {v.get('title', '')}")
                a.triggered.connect(
                    lambda checked=False, src=rec, tgt=v: self.switch_version(src, tgt)
                )
        act_find = menu.addAction("다른 버전 찾기…")

        menu.addSeparator()
        act_open = menu.addAction("폴더 열기")
        if self.playlists:
            pmenu = menu.addMenu("플레이리스트에 추가")
            for pname in self.playlists:
                pa = pmenu.addAction(pname)
                pa.triggered.connect(
                    lambda checked=False, p=pname: self.add_selected_to_playlist(p)
                )
        act_del = menu.addAction("삭제")

        _style_context_menu(menu)
        chosen = menu.exec(self.table.viewport().mapToGlobal(pos))
        if chosen == act_play:
            self.on_play_selected()
        elif chosen == act_find:
            self.on_find_versions(rec)
        elif chosen == act_open:
            _open_in_explorer(str(rec.get("path", "")))
        elif chosen == act_del:
            self.on_delete_selected()

    def switch_version(self, current_rec: dict, target_rec: dict) -> None:
        old_id = str(current_rec.get("id", ""))
        new_id = str(target_rec.get("id", ""))
        if not new_id or old_id == new_id:
            return

        plist = self.current_playlist
        if plist != "All Tracks" and plist in self.playlists:
            ids = [str(x) for x in self.playlists[plist]]
            new_list, replaced = [], False
            for tid in ids:
                if tid == old_id and not replaced:
                    new_list.append(new_id)
                    replaced = True
                elif tid == new_id:
                    continue  # collapse duplicate into the swapped slot
                else:
                    new_list.append(tid)
            if replaced:
                self.playlists[plist] = new_list
                self.save_playlists()

        # Reflect the swap in the live queue and current playback.
        for i, r in enumerate(self.play_queue):
            if str(r.get("id", "")) == old_id:
                self.play_queue[i] = target_rec
        was_playing = (
            getattr(self, "current_playing_record", None) is not None
            and str(self.current_playing_record.get("id", "")) == old_id
        )
        self.render_table()
        if was_playing and os.path.isfile(str(target_rec.get("path", ""))):
            self.play_track_on_current_deck(target_rec)
        self.status.setText(
            f"버전 전환: {self._version_label(target_rec)} — {target_rec.get('title', '')}"
        )

    def on_find_versions(self, rec: dict) -> None:
        base, _ = split_version(rec.get("title", ""))
        initial = f"{rec.get('artist', '')} {base}".strip()
        dlg = VersionFinderDialog(
            self.pool,
            initial,
            self,
            title="다른 버전 찾기",
            hint="Extended / Radio / Original 등 — 받을 버전을 체크하세요.",
        )
        if dlg.exec() != QDialog.Accepted or not dlg.selected:
            return
        group_key = self._effective_group_key(rec)
        self._start_downloads_from_candidates(dlg.selected, group_key=group_key)

    def on_version_downloaded(self, result: object, group_key: str) -> None:
        records = result if isinstance(result, list) else [result]
        title_last = ""
        for rec in records:
            if isinstance(rec, dict) and rec.get("path") and os.path.isfile(rec["path"]):
                rec = dict(rec)
                rec["version_group"] = group_key  # force-link to the source group
                rec["version_label"] = split_version(rec.get("title", ""))[1]
                self.records = upsert_record(self.records, rec)
                title_last = rec.get("title", "")
        self.render_table()
        self.status.setText(f"버전 추가 완료: {title_last}  (우클릭 → 버전 전환)")
        self.progress.setValue(100)

    def on_table_double_clicked(self, index) -> None:
        if index.column() == 3:  # Genre & Tags column
            rec_id = self.table.item(index.row(), 0).data(Qt.UserRole)
            rec = next((r for r in self.records if str(r.get("id")) == str(rec_id)), None)
            if rec:
                self.do_edit_records([rec])
        else:
            self.on_play_selected()

    def on_bulk_edit(self) -> None:
        recs = self.selected_records()
        if not recs:
            QMessageBox.warning(self, "WaveMash", "먼저 곡을 선택해 주세요.")
            return
        self.do_edit_records(recs)
            
    def do_edit_records(self, recs: list) -> None:
        if not recs:
            return
            
        all_existing_tags = set()
        for r in self.records:
            all_existing_tags.update(r.get("tags", []))
            
        dialog = BulkEditDialog(recs, list(all_existing_tags), self)
        if dialog.exec() == QDialog.Accepted:
            updates = dialog.get_updates()
            if not updates:
                return
                
            for rec in recs:
                path = str(rec.get("path", ""))
                if os.path.isfile(path):
                    for k, v in updates.items():
                        if k == "tags":
                            rec[k] = v
                        elif v: # Only update string fields if not empty
                            rec[k] = v
                    self.records = upsert_record(self.records, rec)
                    # Retry cover from URL thumbnail if missing
                    cover_data = None
                    cover_mime = "image/jpeg"
                    try:
                        if rec.get("url"):
                            cover_data, cover_mime = resolve_cover_bytes(
                                {"thumbnail_url": "", "thumbnail": "", "url": rec.get("url", "")} | rec,
                                os.path.join(WAV_ROOT, "_temp"),
                                str(rec.get("id", "")),
                            )
                    except Exception:
                        cover_data = None
                    
                    write_wav_tags(path, rec, cover_data=cover_data, cover_mime=cover_mime)
                    
            self.render_table()
            QMessageBox.information(self, "WaveMash", f"{len(recs)}곡의 태그를 업데이트했습니다.")

    def on_delete_selected(self) -> None:
        recs = self.selected_records()
        if not recs:
            QMessageBox.warning(self, "WaveMash", "먼저 곡을 선택해 주세요.")
            return

        title = recs[0].get("title", "")
        if len(recs) > 1:
            title += f" 외 {len(recs)-1}곡"

        msg = QMessageBox(self)
        msg.setWindowTitle("삭제 확인")
        msg.setText(f'"{title}" 을(를) 삭제할까요?')
        msg.setInformativeText(
            "WAV 파일만 삭제합니다. 같은 폴더의 다른 곡은 유지됩니다."
        )
        msg.setStandardButtons(
            QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Yes
        )
        msg.setDefaultButton(QMessageBox.StandardButton.Cancel)
        yes_btn = msg.button(QMessageBox.StandardButton.Yes)
        cancel_btn = msg.button(QMessageBox.StandardButton.Cancel)
        if yes_btn:
            yes_btn.setText("삭제")
        if cancel_btn:
            cancel_btn.setText("취소")
        if msg.exec() != QMessageBox.StandardButton.Yes:
            return

        delete_ids = {str(r.get("id", "")) for r in recs}
        playing = getattr(self, "current_playing_record", None)
        if playing and str(playing.get("id", "")) in delete_ids:
            self.player_a.stop()
            self.player_b.stop()
            self.current_playing_record = None
            self._np_rec = None

        for rec in recs:
            path = str(rec.get("path", ""))
            delete_track_file(path)
            self.records = delete_record(self.records, str(rec.get("id", "")))

            rec_id = str(rec.get("id", ""))
            for p in self.playlists:
                if rec_id in self.playlists[p]:
                    self.playlists[p].remove(rec_id)

        cleanup_empty_dirs()
        save_archive(self.records)
        self.save_playlists()
        self.render_table()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("WaveMash")
    app.setApplicationDisplayName("WaveMash")
    app.setOrganizationName("WaveMash")
    app.setQuitOnLastWindowClosed(False)

    if try_activate_existing_instance():
        return 0

    win = MainWindow()
    guard = SingleInstanceGuard(win.show_from_tray, win)
    if not guard.listen():
        return 1
    win._single_instance_guard = guard

    win.show()
    return app.exec()
