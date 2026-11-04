@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python 3.10+ is required. Install from https://python.org and run this file again.
  pause
  exit /b 1
)
python -c "import psutil, zeroconf" 2>nul
if errorlevel 1 (
  echo Installing PASADHI dependencies...
  python -m pip install --quiet psutil==7.2.2 zeroconf==0.153.0
)
echo PASADHI settings: http://127.0.0.1:8765
python "pasadhi\app\service.py" --host 0.0.0.0 --port 8765 %*
pause
