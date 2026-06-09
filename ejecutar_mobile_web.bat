@echo off
title VA-Bus Mobile (Web)
echo.
echo  ====================================
echo   Aerorutas de Venezuela - Mobile Web
echo  ====================================
echo.

REM Liberar el puerto 5003: un servidor viejo bloquea archivos y el build sale
REM incompleto (sin index.html). Por eso lo matamos antes de compilar.
echo  [0/2] Liberando puerto 5003...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5003 ^| findstr LISTENING 2^>nul') do taskkill /PID %%a /F >nul 2>&1

cd /d "%~dp0mobile"

echo  [1/2] Compilando build web (release)...
echo  (tarda un par de minutos)
echo.
call flutter build web --release
if errorlevel 1 (
    echo.
    echo  ERROR al compilar. Revisa los mensajes de arriba.
    pause
    exit /b 1
)

echo.
echo  [2/2] Sirviendo en el puerto 5003:
echo    Local:  http://localhost:5003
echo    Tunnel: https://5003.masterslogic.com
echo.
echo  Ctrl+C para detener.
echo.

cd /d "%~dp0mobile\build\web"
python -m http.server 5003 --bind 0.0.0.0
pause
