@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Local AI Transcriber Setup
py -3.12 --version >nul 2>&1
if errorlevel 1 goto python_missing
if not exist ".venv\Scripts\python.exe" (
  echo Creating Python 3.12 environment...
  py -3.12 -m venv .venv
  if errorlevel 1 goto failed
)
echo Installing dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo.
echo Ready. Double-click Run.cmd to launch.
pause
exit /b 0
:python_missing
echo Python 3.12 is required. Install from python.org or run:
echo winget install --id Python.Python.3.12 -e
pause
exit /b 1
:failed
echo Installation failed. See docs\TROUBLESHOOTING.md
pause
exit /b 1
