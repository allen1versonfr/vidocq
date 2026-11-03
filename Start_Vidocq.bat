@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python is required. Install Python 3.10 or newer from python.org.
  echo Then double-click this file again.
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 goto failed
)
".venv\Scripts\python.exe" -c "import webview, PIL" >nul 2>nul
if errorlevel 1 (
  echo First run: installing the native desktop window component...
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Native component unavailable. Opening browser mode instead.
    ".venv\Scripts\python.exe" app.py --browser
    goto end
  )
)
".venv\Scripts\python.exe" app.py
if errorlevel 1 goto failed
goto end
:failed
echo The app could not start. See the error above or read README.md.
pause
:end
endlocal
