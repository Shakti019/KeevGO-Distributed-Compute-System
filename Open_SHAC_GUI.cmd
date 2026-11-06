@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" gui_pyqt/app.py
) else (
    python gui_pyqt/app.py
)
if errorlevel 1 pause
