@echo off
setlocal
cd /d "%~dp0"

echo [WaveMash] Installing build tools...
python -m pip install -q pyinstaller

echo [WaveMash] Building standalone app...
python -m PyInstaller wavemash.spec --noconfirm
if errorlevel 1 (
    echo Build failed.
    exit /b 1
)

echo.
echo Done: dist\WaveMash\WaveMash.exe
echo Copy .env next to WaveMash.exe if you use Spotify API keys.
endlocal
