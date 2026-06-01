@echo off
title VA-Bus - Generar APK
echo.
echo  ====================================
echo   Aerorutas de Venezuela - Generar APK
echo  ====================================
echo.

cd /d "%~dp0mobile"

echo  Limpiando build anterior...
call flutter clean
echo.

echo  Obteniendo dependencias...
call flutter pub get
echo.

echo  Generando APK...
call flutter build apk --release
echo.

if exist "build\app\outputs\flutter-apk\app-release.apk" (
    echo  ====================================
    echo   APK generado exitosamente!
    echo  ====================================
    echo.
    echo   Ubicacion:
    echo   mobile\build\app\outputs\flutter-apk\app-release.apk
    echo.
    explorer "build\app\outputs\flutter-apk"
) else (
    echo  ERROR: No se pudo generar el APK.
)

echo.
pause
