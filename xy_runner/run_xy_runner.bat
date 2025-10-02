@echo off
cd /d "%~dp0"
call .venv_xy_runner\Scripts\activate.bat
python xy_runner.py %*
pause