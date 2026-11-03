@echo off
cd /d "%~dp0"
py -3 -m pip install "Pillow>=12.2.0,<13"
if errorlevel 1 (
  echo Image search dependency installation failed. Text research can still run.
)
py -3 app.py --browser
pause
