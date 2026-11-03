@echo off
setlocal
cd /d "%~dp0"
py -3 -m venv .venv
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller==6.20.0
if errorlevel 1 goto failed
.venv\Scripts\python.exe scripts\build_icon.py
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m unittest discover -s tests -v
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --name Vidocq --icon "build/assets/vidocq.ico" --add-data "build/assets;assets" --add-data "ui;ui" --add-data "source-catalog.json;." --add-data "docs/OSINT_FRAMEWORK_LICENSE.txt;." --add-data "scripts/local_ocr.ps1;scripts" --add-data "scripts/burn_cleanup.ps1;scripts" --collect-all webview --collect-all phonenumbers --collect-all pypdfium2 --collect-all maigret --add-data "docs/MAIGRET_LICENSE.txt;docs" launch.py
if errorlevel 1 goto failed
.venv\Scripts\python.exe scripts\windows_smoke.py
if errorlevel 1 goto failed
echo Built and verified dist\Vidocq.exe
exit /b 0
:failed
echo Build or verification failed.
exit /b 1
