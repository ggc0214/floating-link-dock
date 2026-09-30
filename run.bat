@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%~dp0src"
python -m floating_link_dock.main
exit /b %errorlevel%
