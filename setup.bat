@echo off
cd /d "%~dp0"
echo [1/2] Installing Python dependencies...
pip install -r requirements.txt
echo.
echo [2/2] Installing Spotify support (spotdl)...
call install_spotify.bat
echo.
echo Setup complete. Launch WaveMash with start_desktop.bat
pause
