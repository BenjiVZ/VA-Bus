@echo off
title VA-Bus Mobile (Web)
echo.
echo  ====================================
echo   Aerorutas de Venezuela - Mobile Web
echo  ====================================
echo.
echo  Iniciando app movil en Chrome...
echo  URL: http://localhost:8080
echo.

cd /d "%~dp0mobile"
flutter run -d chrome --web-port=8080
pause
