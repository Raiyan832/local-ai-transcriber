@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run Install.cmd first.
  pause
  exit /b 1
)
echo Optional CUDA 12 / cuDNN 9 runtime packages require a large download.
echo Requires a compatible NVIDIA GPU and recent NVIDIA driver.
choice /c YN /n /m "Proceed? [Y/N] "
if errorlevel 2 exit /b 0
".venv\Scripts\python.exe" -m pip install "nvidia-cublas-cu12==12.9.2.10" "nvidia-cudnn-cu12==9.27.0.42"
if errorlevel 1 (
 echo Installation failed.
 pause
 exit /b 1
)
echo Use Run.cmd and click Test Hardware to verify CUDA FP16 inference.
pause
