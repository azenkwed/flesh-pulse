#!/usr/bin/env bash
set -euo pipefail

echo ""
echo " ════════════════════════════════════"
echo " SEX HEALTH NEWS"
echo " ════════════════════════════════════"
echo ""

# Check for .env file
if [ ! -f .env ]; then
    echo "[!] No .env file found. Copy .env.example to .env and add your API keys."
    exit 1
fi

# Create virtual environment if it doesn't exist
VENV=".venv"
if [ ! -d "$VENV" ]; then
    echo "[*] Creating virtual environment in $VENV..."
    python3 -m venv "$VENV"
fi

# Activate virtual environment
echo "[*] Activating virtual environment..."
source "$VENV/bin/activate"

# Install/upgrade dependencies
echo "[*] Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo "[✓] Ready! Starting Sex Health News on http://0.0.0.0:8000"
echo ""

# Start the app with auto-reload for development
exec python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
