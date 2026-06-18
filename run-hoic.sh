#!/usr/bin/env bash
# HOIC Launcher for Linux / macOS

set -e

if [ ! -d ".venv" ]; then
    echo "[HOIC] Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

if ! python -c "import customtkinter; import aiohttp" 2>/dev/null; then
    echo "[HOIC] Installing dependencies..."
    pip install -r requirements.txt
fi

echo "[HOIC] Launching..."
python hoic.py
