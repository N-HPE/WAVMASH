"""Shared Qt menu styling."""
from __future__ import annotations

from PySide6.QtWidgets import QMenu

DARK_MENU_QSS = """
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


def style_context_menu(menu: QMenu) -> None:
    menu.setStyleSheet(DARK_MENU_QSS)
    for action in menu.actions():
        sub = action.menu()
        if sub is not None:
            style_context_menu(sub)
