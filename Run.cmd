@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Install the app first with Install.cmd
  pause
  exit /b 1
)
".venv\Scripts\python.exe" "LocalAITranscriber.pyw"
if errorlevel 1 pause
