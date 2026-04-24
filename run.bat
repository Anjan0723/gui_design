@echo off
REM Run LDC1101 GUI Application
REM Make sure you're in the correct directory
cd /d "%~dp0"

REM Activate virtual environment and run
call .venv\Scripts\activate.bat
python main.py

REM If python not found in venv, try direct path
if errorlevel 1 (
    .venv\Scripts\python.exe main.py
)