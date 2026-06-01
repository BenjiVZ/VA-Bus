@echo off
title VA-Bus Mobile (Web)
echo.
echo  ====================================
echo   Aerorutas de Venezuela - Mobile Web
echo  ====================================
echo.

cd /d "%~dp0mobile"

echo  [1/2] Compilando build web (release)...
echo  (la primera vez tarda un par de minutos)
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

python -m http.server 5003 --bind 0.0.0.0 --directory "%~dp0mobile\build\web"
pause
