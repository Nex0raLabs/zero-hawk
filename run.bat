@echo off
setlocal
cd /d "%~dp0"
title ZERO HAWK - Local Prospecting Workspace
echo.
echo  ============================================
echo              ZERO HAWK
echo       Local-first prospecting workspace
echo  ============================================
echo.
where py >nul 2>nul
if errorlevel 1 (
  echo Python Launcher not found. Install Python 3.11+ from python.org and enable PATH.
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe (
  echo [1/3] Creating Python environment...
  py -3 -m venv .venv
  if errorlevel 1 goto error
)
call .venv\Scripts\activate.bat
echo [2/3] Installing Zero Hawk...
python -m pip install --upgrade pip
if errorlevel 1 goto error
python -m pip install -e ".[mcp]"
if errorlevel 1 goto error
if not exist .env copy .env.example .env >nul
echo [3/3] Starting your private dashboard...
zero-hawk dashboard
goto end
:error
echo.
echo Setup did not complete. Read the error above, then see README.md Troubleshooting.
pause
exit /b 1
:end
endlocal
