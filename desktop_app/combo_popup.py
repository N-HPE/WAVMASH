"""QComboBox popup styling and hover delegate (Windows-friendly)."""
from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt, QSize, QStringListModel
from PySide6.QtGui import QColor, QPainter, QPalette
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QStyledItemDelegate,
    QStyleOptionViewItem,
)


class ComboPopupDelegate(QStyledItemDelegate):
    """Paint combo popup rows with explicit hover (QSS :hover is unreliable on Windows)."""

    _BG_NORMAL = QColor("#2d2d2d")
    _BG_HOVER = QColor("#37373d")
    _BG_CURRENT = QColor("#094771")
    _FG_NORMAL = QColor("#e8e8e8")
    _FG_ACTIVE = QColor("#ffffff")

    def __init__(self, combo: QComboBox) -> None:
        view = combo.view()
        super().__init__(view if view is not None else combo)
        self._combo = combo
        self._hover_row = -1
        combo.highlighted.connect(self._on_highlighted)

    def _on_highlighted(self, row: int) -> None:
        self._set_hover_row(row)

    def _set_hover_row(self, row: int) -> None:
        if row == self._hover_row:
            return
        view = self._combo.view()
        model = self._combo.model()
        col = self._combo.modelColumn()
        old = self._hover_row
        self._hover_row = row
        if view is None or model is None:
            return
        for r in {old, row}:
            if r >= 0:
                view.update(model.index(r, col))

    def reset_hover(self) -> None:
        self._set_hover_row(-1)

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionViewItem,
        index,
    ) -> None:
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        row = index.row()
        cur = self._combo.currentIndex()
        if row == cur:
            bg, fg = self._BG_CURRENT, self._FG_ACTIVE
        elif row == self._hover_row:
            bg, fg = self._BG_HOVER, self._FG_ACTIVE
        else:
            bg, fg = self._BG_NORMAL, self._FG_NORMAL
        painter.fillRect(opt.rect, bg)
        painter.setPen(fg)
        text = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        text_rect = opt.rect.adjusted(8, 0, -8, 0)
        painter.drawText(
            text_rect,
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            text,
        )

    def sizeHint(self, option: QStyleOptionViewItem, index):
        width = option.rect.width() if option.rect.width() > 0 else 220
        return QSize(width, 28)


def _hook_combo_popup_lifecycle(combo: QComboBox, delegate: ComboPopupDelegate) -> None:
    if getattr(combo, "_wm_popup_lifecycle", False):
        return
    combo._wm_popup_lifecycle = True

    orig_show = combo.showPopup

    def show_popup() -> None:
        delegate.reset_hover()
        orig_show()
        view = combo.view()
        if view is not None:
            view.setItemDelegate(delegate)
            view.setMouseTracking(True)
            view.viewport().setMouseTracking(True)

    combo.showPopup = show_popup  # type: ignore[method-assign]

    view = combo.view()
    if view is None:
        return

    class _ViewportHoverFilter(QObject):
        def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
            if event.type() == QEvent.Type.MouseMove:
                pos = (
                    event.position().toPoint()
                    if hasattr(event, "position")
                    else event.pos()
                )
                idx = view.indexAt(pos)
                delegate._set_hover_row(idx.row() if idx.isValid() else -1)
            elif event.type() == QEvent.Type.Leave:
                delegate.reset_hover()
            return False

    move_filter = _ViewportHoverFilter(view)
    view.viewport().installEventFilter(move_filter)
    combo._wm_viewport_hover_filter = move_filter

    popup_win = view.window()
    if popup_win is None or popup_win is view:
        return

    class _PopupHideFilter(QObject):
        def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
            if event.type() in (QEvent.Type.Hide, QEvent.Type.Close):
                delegate.reset_hover()
            return False

    hide_filter = _PopupHideFilter(popup_win)
    popup_win.installEventFilter(hide_filter)
    combo._wm_popup_hide_filter = hide_filter


def style_combo_popup(combo: QComboBox) -> None:
    """Dark popup list with reliable row hover on Windows."""
    view = combo.view()
    if view is None:
        return
    view.setAutoFillBackground(True)
    view.setMouseTracking(True)
    view.viewport().setMouseTracking(True)
    pal = view.palette()
    pal.setColor(QPalette.ColorRole.Base, QColor("#2d2d2d"))
    pal.setColor(QPalette.ColorRole.Window, QColor("#2d2d2d"))
    pal.setColor(QPalette.ColorRole.Text, QColor("#e8e8e8"))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor("#e8e8e8"))
    pal.setColor(QPalette.ColorRole.Highlight, QColor("#094771"))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    view.setPalette(pal)
    view.setStyleSheet(
        """
        QAbstractItemView {
            background-color: #2d2d2d;
            color: #e8e8e8;
            outline: none;
            padding: 2px;
            border: 1px solid #444444;
        }
        """
    )

    delegate = getattr(combo, "_wm_popup_delegate", None)
    if delegate is None:
        delegate = ComboPopupDelegate(combo)
        combo._wm_popup_delegate = delegate
        _hook_combo_popup_lifecycle(combo, delegate)
    view.setItemDelegate(delegate)


def configure_compact_combo(combo: QComboBox) -> None:
    """Ingest playlist selector: no arrow button (avoids white native chrome on Windows)."""
    combo.setObjectName("compactCombo")
    style_combo_popup(combo)


def wire_filterable_combo(combo: QComboBox, presets: list[str]) -> None:
    """Editable combo: narrow dropdown and completer while typing (call after style_combo_popup)."""
    master: list[str] = []
    seen: set[str] = set()
    for item in presets:
        if item not in seen:
            seen.add(item)
            master.append(item)

    initial = combo.currentText().strip()
    if initial and initial not in seen:
        master.append(initial)
        seen.add(initial)

    completer_model = QStringListModel([x for x in master if x])
    completer = QCompleter(completer_model, combo)
    completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
    completer.setFilterMode(Qt.MatchFlag.MatchContains)
    completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
    combo.setCompleter(completer)

    def filtered_items(needle: str) -> list[str]:
        n = needle.strip().casefold()
        if not n:
            return list(master)
        return [x for x in master if x and n in x.casefold()]

    def repopulate(keep_text: str | None = None) -> None:
        text = combo.currentText() if keep_text is None else keep_text
        items = filtered_items(text)
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(items)
        line = combo.lineEdit()
        if line is not None:
            line.setText(text)
        combo.blockSignals(False)
        completer_model.setStringList([x for x in items if x])

    line = combo.lineEdit()
    if line is not None:
        line.textChanged.connect(repopulate)

    if not getattr(combo, "_wm_filter_show_wrapped", False):
        combo._wm_filter_show_wrapped = True
        orig_show = combo.showPopup

        def show_popup() -> None:
            repopulate()
            orig_show()

        combo.showPopup = show_popup  # type: ignore[method-assign]

    repopulate()
