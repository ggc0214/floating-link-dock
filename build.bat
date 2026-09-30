@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%~dp0src"

python -m pytest tests -q
if errorlevel 1 exit /b %errorlevel%

python scripts\generate_icon.py
if errorlevel 1 exit /b %errorlevel%

python -m PyInstaller --clean --noconfirm FloatingLinkDock.spec
if errorlevel 1 exit /b %errorlevel%

echo.
echo Build complete: dist\FloatingLinkDock.exe
exit /b 0
