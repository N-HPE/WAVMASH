"""Track metadata and YouTube version-picker dialogs."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from desktop_app.combo_popup import style_combo_popup, wire_filterable_combo
from desktop_app.track_widgets import TagInputWidget
from desktop_app.workers import WorkerPool

DEFAULT_GENRE_PRESETS = [
    "",
    "Pop",
    "Dance",
    "Electronic",
    "Classical",
    "Jazz",
    "Hip-Hop",
    "R&B",
    "Rock",
    "Latin",
    "Country",
    "K-Pop",
    "J-Pop",
    "Indie",
    "Ambient",
    "Acoustic",
]


def build_genre_presets(
    library_records: list[dict[str, Any]] | None = None,
    *,
    extra: list[str] | None = None,
) -> list[str]:
    """Preset list for genre combo: defaults + genres already used in the library."""
    out: list[str] = []
    seen: set[str] = set()
    for item in DEFAULT_GENRE_PRESETS:
        if item not in seen:
            seen.add(item)
            out.append(item)
    for source in (extra or []):
        g = (source or "").strip()
        if g and g not in seen:
            seen.add(g)
            out.append(g)
    if library_records:
        used = sorted(
            {
                str(r.get("genre", "")).strip()
                for r in library_records
                if str(r.get("genre", "")).strip()
            },
            key=str.casefold,
        )
        for g in used:
            if g not in seen:
                seen.add(g)
                out.append(g)
    return out


class BulkEditDialog(QDialog):
    def __init__(
        self,
        records: list[dict[str, Any]],
        all_existing_tags: list[str],
        parent: QWidget | None = None,
        *,
        genre_presets: list[str] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setModal(True)
        self.resize(600, 450)
        self.setMinimumWidth(500)
        self.records = records
        self.all_existing_tags = all_existing_tags

        layout = QVBoxLayout(self)

        if len(records) == 1:
            self.setWindowTitle("곡 상세정보")
            title = records[0].get("title", "") or "제목 없음"
            layout.addWidget(QLabel(f"<b>{title}</b>"))
        else:
            self.setWindowTitle("다중 태그 편집")
            layout.addWidget(QLabel(f"{len(records)}개의 곡을 선택하셨습니다."))

        form = QFormLayout()
        self.artist_edit = QLineEdit()
        self.album_edit = QLineEdit()
        self.genre_edit = QComboBox()
        self.genre_edit.setEditable(True)
        presets = genre_presets or build_genre_presets(
            extra=[str(r.get("genre", "")) for r in records]
        )
        self.genre_edit.lineEdit().setPlaceholderText("메인 장르 선택 또는 입력...")
        if len(records) == 1:
            self.artist_edit.setText(records[0].get("artist", ""))
            self.album_edit.setText(records[0].get("album", ""))
            self.genre_edit.setCurrentText(records[0].get("genre", ""))
        style_combo_popup(self.genre_edit)
        wire_filterable_combo(self.genre_edit, presets)

        form.addRow("Artist:", self.artist_edit)
        form.addRow("Album:", self.album_edit)
        form.addRow("Main Genre:", self.genre_edit)
        layout.addLayout(form)

        layout.addWidget(QLabel("특징 태그 (Tags):"))

        all_tags: list[str] = []
        for r in records:
            all_tags.extend(r.get("tags", []))

        self.tag_input = TagInputWidget(self.all_existing_tags, set(all_tags))
        layout.addWidget(self.tag_input)

        buttons = QHBoxLayout()
        cancel = QPushButton("Cancel")
        ok = QPushButton("Apply")
        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self.accept)
        buttons.addStretch(1)
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        layout.addLayout(buttons)

    def get_updates(self) -> dict[str, Any]:
        updates: dict[str, Any] = {}
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
        title: str = "YouTube Search",
        hint: str = "Enter a query and check videos to download.",
        ok_label: str = "Download selected",
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
        self.search_btn = QPushButton("Search")
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
        self.cancel_btn = QPushButton("Cancel")
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
            item.setData(Qt.ItemDataRole.UserRole, c)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.list.addItem(item)

    def on_search_failed(self, err: str) -> None:
        self.search_btn.setEnabled(True)
        self.hint.setText(f"검색 실패: {err}")

    def accept_selection(self) -> None:
        chosen = []
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it is not None and it.checkState() == Qt.CheckState.Checked:
                chosen.append(it.data(Qt.ItemDataRole.UserRole))
        if not chosen:
            self.hint.setText("받을 영상을 하나 이상 체크해 주세요.")
            return
        self.selected = chosen
        self.accept()
