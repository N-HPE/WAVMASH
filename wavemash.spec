# -*- mode: python ; coding: utf-8 -*-
"""Build WaveMash standalone app: pyinstaller wavemash.spec"""

import sys
from pathlib import Path

root = Path(SPECPATH)

a = Analysis(
    [str(root / "desktop_app" / "__main__.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[
        (str(root / "icon_large.ico"), "."),
    ],
    hiddenimports=[
        "paths",
        "env_loader",
        "library",
        "pipeline",
        "spotify_pipeline",
        "spotify_metadata",
        "track_metadata",
        "desktop_app.app",
        "desktop_app.workers",
        "desktop_app.archive_store",
        "desktop_app.waveform",
        "desktop_app.ipod_controls",
        "desktop_app.analysis",
        "yt_dlp",
        "static_ffmpeg",
        "mutagen",
        "requests",
        "spotdl",
        "spotdl.utils.search",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "numpy.distutils"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="WaveMash",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(root / "icon_large.ico") if (root / "icon_large.ico").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="WaveMash",
)
