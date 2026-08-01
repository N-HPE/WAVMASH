@echo off
title WaveMash Server
color 0A

echo.
echo  ============================================
echo          W A V E M A S H   S E R V E R
echo  ============================================
echo.
echo  Starting all services in this window...
echo  (Press Ctrl+C and type 'Y' to stop the servers)
echo.

cd /d "%~dp0"

if exist ".venv\Scripts\activate.bat" (
  call ".venv\Scripts\activate.bat"
)

if not exist ".env" (
  echo  [!] .env 가 없습니다. .env.example 을 복사해 API 키를 넣어 주세요.
  pause
  exit /b 1
)

if not exist "web\node_modules" (
  echo  Installing frontend deps...
  call npm --prefix web install
)

:: Open browser slightly delayed in the background
start /B cmd /c "timeout /t 5 >nul && start """" ""http://localhost:3000"""

:: Use concurrently to run both backend and frontend in the same window
npx --prefix web concurrently -n "FastAPI,Next.js" -c "cyan,green" "python -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload" "npm --prefix web run dev"
