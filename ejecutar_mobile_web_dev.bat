@echo off
title VA-Bus Mobile (Web DEV - hot reload)
echo.
echo  ============================================
echo   Aerorutas Mobile - DESARROLLO (hot reload)
echo  ============================================
echo.
echo  Modo desarrollo: NO compila release, refleja tus cambios al vuelo.
echo.
echo  URL: http://localhost:8080
echo.
echo  Comandos mientras corre:
echo     r  = hot reload (aplicar cambios)
echo     R  = hot restart (reinicio completo)
echo     q  = salir
echo.
echo  La primera carga (debug) tarda; los cambios despues son instantaneos.
echo.

cd /d "%~dp0mobile"
flutter run -d web-server --web-port=8080 --web-hostname=0.0.0.0
pause
