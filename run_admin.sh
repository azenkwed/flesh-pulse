#!/usr/bin/env bash
set -euo pipefail

echo ""
echo " ════════════════════════════════════"
echo " SEX HEALTH NEWS — ADMIN DASHBOARD"
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

echo "[✓] Ready! Starting admin dashboard on http://127.0.0.1:8001"
echo ""

# Start the admin app (local-only, not exposed to the internet)
exec python -m uvicorn admin.app:app --host 127.0.0.1 --port 8001 --reload
