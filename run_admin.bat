@echo off
chcp 65001 >nul
echo.
echo  ========================
echo  PANOPTIQA ADMIN
echo  ========================
echo.

if not exist .env (
    echo [!] No .env file found. Copy .env.example to .env and add your API keys.
    pause
    exit /b 1
)

if not exist .venv (
    echo [*] Creating virtual environment...
    python -m venv .venv
)

echo [*] Activating virtual environment...
call .venv\Scripts\activate.bat

echo [*] Installing dependencies...
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

python -m uvicorn admin.app:app --host 127.0.0.1 --port 8001 --reload
