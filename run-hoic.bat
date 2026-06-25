@echo off
REM HOIC Launcher for Windows
REM Auto-creates venv and installs deps on first run

setlocal

set VENV_DIR=.venv
set PY=python

if not exist "%VENV_DIR%\Scripts\python.exe" (
    echo [HOIC] Creating virtual environment...
    %PY% -m venv %VENV_DIR%
    if errorlevel 1 (
        echo [HOIC] Failed to create venv. Ensure Python 3.10+ is installed and in PATH.
        pause
        exit /b 1
    )
)

set VPY=%VENV_DIR%\Scripts\python.exe

echo [HOIC] Checking / installing dependencies...
%VPY% -m pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo [HOIC] pip install had issues. Trying without quiet...
    %VPY% -m pip install -r requirements.txt
)

echo [HOIC] Launching...
%VPY% hoic.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [HOIC] Failed to start. Check errors above.
    echo You may need to run:  .venv\Scripts\python -m pip install -r requirements.txt
    echo.
    pause
)
