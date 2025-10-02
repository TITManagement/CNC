@echo off
cd /d "%~dp0"
call .venv_xyz_runner\Scripts\activate.bat
python xyz_runner.py %*
pause