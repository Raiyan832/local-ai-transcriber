@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run Install.cmd first.
  pause
  exit /b 1
)
where ffmpeg >nul 2>&1
if errorlevel 1 (
  echo Install FFmpeg with: winget install --id Gyan.FFmpeg -e
  pause
  exit /b 1
)
where ffprobe >nul 2>&1
if errorlevel 1 (
  echo FFprobe is missing. Reinstall FFmpeg.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" "converter.py"
if errorlevel 1 pause
