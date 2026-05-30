@echo off
cd /d "%~dp0"
title WaveMash Live Dev Server
echo =========================================
echo  WaveMash Development Live-Reload Server
echo =========================================
echo.
python dev.py
pause
