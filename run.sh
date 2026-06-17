#!/usr/bin/env bash
set -euo pipefail

echo ""
echo " ========================"
echo " FLESH PULSE"
echo " ========================"
echo ""

if [ ! -f .env ]; then
    echo "[!] No .env file found. Copy .env.example to .env and add your API keys."
    exit 1
fi

VENV=".venv"

if [ ! -d "$VENV" ]; then
    echo "[*] Creating virtual environment..."
    python3 -m venv "$VENV"
fi

echo "[*] Activating virtual environment..."
source "$VENV/bin/activate"

echo "[*] Installing dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

exec python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
