"""Project root — works for source checkout and PyInstaller builds."""

from __future__ import annotations

import os
import sys


def project_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


PROJECT_DIR = project_dir()
