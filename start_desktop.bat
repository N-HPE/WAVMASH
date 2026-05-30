@echo off
cd /d "%~dp0"
title WaveMash Desktop
echo WaveMash Desktop starting...
python -m desktop_app
echo.
echo (If it closes immediately, open desktop_app.log)
pause

