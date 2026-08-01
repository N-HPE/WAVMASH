"""Library-wide search: tracks, playlists, tags, sets — grouped results."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from desktop_app.set_model import DJSet

def _apply_dark_list_palette(widget) -> None:
    pal = widget.palette()
    pal.setColor(QPalette.ColorRole.Base, QColor("#2d2d2d"))
    pal.setColor(QPalette.ColorRole.Window, QColor("#2d2d2d"))
    pal.setColor(QPalette.ColorRole.Text, QColor("#e8e8e8"))
    pal.setColor(QPalette.ColorRole.Highlight, QColor("#094771"))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    widget.setPalette(pal)
    widget.setAutoFillBackground(True)


_SEARCH_BAR_QSS = """
    QWidget#librarySearchResults {
        background-color: #252526;
        border: 1px solid #3a3a44;
        border-radius: 6px;
    }
    QScrollArea#librarySearchScroll {
        background-color: #252526;
        border: none;
    }
    QWidget#librarySearchResultsHost {
        background-color: #252526;
    }
    QLineEdit#librarySearchEdit {
        background: #1a1a1e;
        border: 1px solid #3a3a44;
        border-radius: 6px;
        padding: 8px 10px;
        color: #ececee;
        font-size: 13px;
    }
    QLineEdit#librarySearchEdit:focus {
        border: 1px solid #007acc;
    }
    QLabel#librarySearchHint {
        color: #7a7a88;
        font-size: 11px;
        background: transparent;
        padding: 2px 4px;
    }
    QLabel#librarySearchSection {
        color: #9a9aa8;
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.6px;
        padding: 8px 4px 2px 4px;
        background: transparent;
    }
    QListWidget#librarySearchList {
        background: transparent;
        border: none;
        outline: none;
        color: #e0e0e8;
        font-size: 12px;
    }
    QListWidget#librarySearchList::item {
        padding: 6px 8px;
        border-radius: 4px;
    }
    QListWidget#librarySearchList::item:selected {
        background: #094771;
        color: #ffffff;
    }
    QListWidget#librarySearchList::item:hover {
        background: #37373d;
    }
"""


@dataclass
class LibrarySearchResults:
    tracks: list[dict[str, Any]] = field(default_factory=list)
    playlists: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    sets: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not (self.tracks or self.playlists or self.tags or self.sets)

    @property
    def total(self) -> int:
        return len(self.tracks) + len(self.playlists) + len(self.tags) + len(self.sets)


def search_library(
    query: str,
    records: list[dict[str, Any]],
    playlists: dict[str, list[str]],
    sets: dict[str, DJSet],
) -> LibrarySearchResults:
    needle = query.strip().casefold()
    if not needle:
        return LibrarySearchResults()

    out = LibrarySearchResults()
    tag_hits: set[str] = set()

    for rec in records:
        title = str(rec.get("title", "") or "")
        artist = str(rec.get("artist", "") or "")
        album = str(rec.get("album", "") or "")
        genre = str(rec.get("genre", "") or "")
        tags = [str(t) for t in (rec.get("tags") or []) if t]

        track_blob = " ".join([title, artist, album, genre, *tags]).casefold()
        if needle in track_blob:
            out.tracks.append(rec)

        for tag in tags:
            tcf = tag.casefold()
            if needle in tcf or tcf in needle:
                tag_hits.add(tag)

    for name in playlists:
        if name == "All Tracks":
            continue
        if needle in name.casefold():
            out.playlists.append(name)

    for name in sets:
        if needle in name.casefold():
            out.sets.append(name)

    out.tags = sorted(tag_hits, key=str.casefold)
    out.playlists.sort(key=str.casefold)
    out.sets.sort(key=str.casefold)
    return out


class LibrarySearchBar(QWidget):
    """Search field above the track list."""

    search_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("librarySearchEdit")
        self.search_edit.setPlaceholderText("곡 · 플리 · 태그 검색…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(lambda t: self.search_changed.emit(t.strip()))
        lay.addWidget(self.search_edit)
        self.setStyleSheet(_SEARCH_BAR_QSS)

    def query(self) -> str:
        return self.search_edit.text().strip()

    def clear_search(self) -> None:
        self.search_edit.blockSignals(True)
        self.search_edit.clear()
        self.search_edit.blockSignals(False)


class LibrarySearchResultsPanel(QWidget):
    """Grouped hits shown between search bar and track table."""

    result_activated = Signal(str, object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("librarySearchResults")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 4, 0, 4)
        root.setSpacing(0)

        self._scroll = QScrollArea()
        self._scroll.setObjectName("librarySearchScroll")
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setMinimumHeight(80)
        self._scroll.setMaximumHeight(280)
        _apply_dark_list_palette(self._scroll)

        self._results_host = QWidget()
        self._results_host.setObjectName("librarySearchResultsHost")
        _apply_dark_list_palette(self._results_host)
        self._results_layout = QVBoxLayout(self._results_host)
        self._results_layout.setContentsMargins(8, 6, 8, 6)
        self._results_layout.setSpacing(4)
        self._scroll.setWidget(self._results_host)
        root.addWidget(self._scroll, 1)

        self._empty_label = QLabel("검색 결과가 없습니다.")
        self._empty_label.setObjectName("librarySearchHint")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.hide()

        self.setStyleSheet(_SEARCH_BAR_QSS)
        _apply_dark_list_palette(self)
        self.hide()

    def present_results(self, results: LibrarySearchResults) -> None:
        self._clear_results_layout()
        self.show()
        if results.is_empty:
            self._results_layout.addWidget(self._empty_label)
            self._empty_label.show()
            return

        self._empty_label.hide()
        if results.tracks:
            self._add_section("TRACKS", results.tracks, "track", self._track_label)
        if results.playlists:
            self._add_section("PLAYLISTS", results.playlists, "playlist", lambda x: str(x))
        if results.tags:
            self._add_section("TAGS", results.tags, "tag", lambda x: f"#{x}")
        if results.sets:
            self._add_section("SETS", results.sets, "set", lambda x: str(x))
        self._results_layout.addStretch(1)

    def clear_results(self) -> None:
        self._clear_results_layout()
        self.hide()

    @staticmethod
    def _track_label(rec: dict[str, Any]) -> str:
        title = str(rec.get("title", "") or "Unknown")
        artist = str(rec.get("artist", "") or "")
        return f"{title} — {artist}" if artist else title

    def _add_section(
        self,
        title: str,
        items: list,
        kind: str,
        label_fn: Callable[[Any], str],
    ) -> None:
        header = QLabel(title)
        header.setObjectName("librarySearchSection")
        self._results_layout.addWidget(header)

        lst = QListWidget()
        lst.setObjectName("librarySearchList")
        lst.setFrameShape(QFrame.NoFrame)
        lst.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        lst.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        row_h = 28
        lst.setMinimumHeight(min(28 * max(2, len(items)), 160))
        lst.setMaximumHeight(min(28 * len(items) + 8, 200))
        _apply_dark_list_palette(lst)

        for item in items:
            li = QListWidgetItem(label_fn(item))
            li.setData(Qt.ItemDataRole.UserRole, (kind, item))
            lst.addItem(li)

        lst.itemClicked.connect(lambda it, k=kind: self._on_item(it, k))
        self._results_layout.addWidget(lst)

    def _on_item(self, item: QListWidgetItem, kind: str) -> None:
        payload = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(payload, tuple) and len(payload) == 2:
            _, data = payload
            self.result_activated.emit(kind, data)

    def _clear_results_layout(self) -> None:
        self._empty_label.hide()
        while self._results_layout.count():
            child = self._results_layout.takeAt(0)
            w = child.widget()
            if w is not None and w is not self._empty_label:
                w.deleteLater()
