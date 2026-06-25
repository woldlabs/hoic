#!/usr/bin/env bash
# HOIC Launcher for Linux / macOS

set -e

PYTHON=${PYTHON:-python3}

if [ ! -d ".venv" ]; then
    echo "[HOIC] Creating virtual environment..."
    $PYTHON -m venv .venv
fi

# shellcheck source=/dev/null
source .venv/bin/activate

if ! python -c "import customtkinter; import aiohttp; from PIL import Image" 2>/dev/null; then
    echo "[HOIC] Installing dependencies..."
    pip install -r requirements.txt
fi

echo "[HOIC] Launching HOIC (Windows + Linux supported)..."
python hoic.py
