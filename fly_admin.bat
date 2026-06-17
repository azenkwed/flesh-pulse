@echo off
chcp 65001 >nul
echo.
echo  ========================
echo  FLESH PULSE ADMIN (Fly.io)
echo  ========================
echo.
echo [*] Opening tunnel to flesh-pulse on Fly.io...
echo [*] Dashboard will be available at http://localhost:8001
echo [*] Press Ctrl+C to close the tunnel.
echo.
fly proxy 8001:8001 -a flesh-pulse
