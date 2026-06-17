@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul

echo.
echo  ════════════════════════════════════
echo  SEX HEALTH NEWS — ADMIN DASHBOARD
echo  ════════════════════════════════════
echo.

:: Check for .env file
if not exist .env (
    echo [!] No .env file found. Copy .env.example to .env and add your API keys.
    pause
    exit /b 1
)

:: Create virtual environment if it doesn't exist
if not exist .venv (
    echo [*] Creating virtual environment...
    python -m venv .venv
    if !errorlevel! neq 0 (
        echo [!] Failed to create virtual environment.
        echo     Make sure Python 3.10+ is installed and in your PATH.
        pause
        exit /b 1
    )
)

:: Activate virtual environment
echo [*] Activating virtual environment...
call .venv\Scripts\activate.bat
if !errorlevel! neq 0 (
    echo [!] Failed to activate virtual environment.
    pause
    exit /b 1
)

:: Install/upgrade dependencies
echo [*] Installing dependencies...
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt

echo [OK] Ready! Starting admin dashboard on http://127.0.0.1:8001
echo.

:: Start the admin app (local-only, not exposed to the internet)
python -m uvicorn admin.app:app --host 127.0.0.1 --port 8001 --reload
