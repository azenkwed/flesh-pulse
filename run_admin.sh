#!/usr/bin/env bash
set -euo pipefail

echo ""
echo " ========================"
echo " PANOPTIQA ADMIN"
echo " ========================"
echo ""

if [ ! -f .env ]; then
    echo "[!] No .env file found. Copy .env.example to .env and add your API keys."
    exit 1
fi

VENV=".venv"

if [ ! -d "$VENV" ]; then
    echo "[!] Virtual environment not found. Run ./run.sh or make install first."
    exit 1
fi

source "$VENV/bin/activate"

echo "[*] Starting admin dashboard on http://127.0.0.1:8001"
echo ""
exec python -m uvicorn admin.app:app --host 127.0.0.1 --port 8001 --reload
