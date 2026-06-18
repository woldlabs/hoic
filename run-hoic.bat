@echo off
REM HOIC Launcher for Windows
REM Run this after first-time "pip install -r requirements.txt"

python hoic.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [HOIC] Failed to start. Make sure you have installed dependencies:
    echo     pip install -r requirements.txt
    echo.
    pause
)
