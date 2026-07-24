@echo off
REM ============================================================
REM  Aerorutas de Venezuela - Validador de SALIDAS
REM  Menu para revisar por que una sucursal sale (o no) como
REM  origen en la web/app. Usa el comando Django "salidas".
REM ============================================================
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
title Aerorutas - Validar salidas
set "PY=%~dp0backend\venv\Scripts\python.exe"
set "MANAGE=%~dp0backend\manage.py"

if not exist "%PY%" (
    echo  [ERROR] No se encontro el entorno de Python en:
    echo          %PY%
    echo  Crea/instala el venv del backend antes de usar esto.
    pause
    exit /b 1
)

:menu
cls
echo.
echo  ============================================================
echo    AERORUTAS - VALIDADOR DE SALIDAS
echo  ============================================================
echo.
echo    --- Diagnostico rapido (lo que preguntaste) ---
echo    1. Diagnostico EL VIGIA
echo    2. Diagnostico MERIDA
echo.
echo    --- Consultas ---
echo    3. Ver todas las oficinas
echo    4. Buscar una oficina por nombre/codigo
echo    5. Diagnostico de CUALQUIER oficina
echo    6. Salidas EN VIVO desde una oficina (origen)
echo    7. Llegadas EN VIVO hacia una oficina (destino)
echo    8. Ver catalogo precargado (lo que ve la web)
echo    9. Mapear un dia: comparar VIVO vs la PAGINA (detallado)
echo   10. Resumen: que origenes salen y cuales NO (y por que)
echo   11. Mapear TODO: incluye ocultos (precio 0) y pares sin respuesta
echo.
echo    0. Salir
echo.
set /p "op=  Elige una opcion: "

if "%op%"=="1" goto vigia
if "%op%"=="2" goto merida
if "%op%"=="3" goto oficinas
if "%op%"=="4" goto buscar
if "%op%"=="5" goto diagnostico
if "%op%"=="6" goto origen
if "%op%"=="7" goto destino
if "%op%"=="8" goto snapshot
if "%op%"=="9" goto mapa
if "%op%"=="10" goto resumen
if "%op%"=="11" goto mapatodo
if "%op%"=="0" exit /b 0
goto menu

:pedir_fecha
REM Deja FARG vacio (=hoy) o "--fecha YYYY-MM-DD"
set "FARG="
set /p "fecha=  Fecha (YYYY-MM-DD) o Enter = hoy: "
if not "%fecha%"=="" set "FARG=--fecha %fecha%"
set "fecha="
goto :eof

:vigia
cls
call :pedir_fecha
echo.
"%PY%" "%MANAGE%" salidas diagnostico "el vigia" %FARG%
echo.
pause
goto menu

:merida
cls
call :pedir_fecha
echo.
"%PY%" "%MANAGE%" salidas diagnostico "merida" %FARG%
echo.
pause
goto menu

:oficinas
cls
"%PY%" "%MANAGE%" salidas oficinas
echo.
pause
goto menu

:buscar
cls
set /p "term=  Texto a buscar (ej. vigia, merida, cara): "
echo.
"%PY%" "%MANAGE%" salidas buscar "%term%"
set "term="
echo.
pause
goto menu

:diagnostico
cls
set /p "term=  Oficina (codofi o nombre, ej. 09 o el vigia): "
call :pedir_fecha
echo.
"%PY%" "%MANAGE%" salidas diagnostico "%term%" %FARG%
set "term="
echo.
pause
goto menu

:origen
cls
set /p "term=  Oficina de ORIGEN (codofi o nombre): "
call :pedir_fecha
echo.
"%PY%" "%MANAGE%" salidas origen "%term%" %FARG%
set "term="
echo.
pause
goto menu

:destino
cls
set /p "term=  Oficina de DESTINO (codofi o nombre): "
call :pedir_fecha
echo.
"%PY%" "%MANAGE%" salidas destino "%term%" %FARG%
set "term="
echo.
pause
goto menu

:snapshot
cls
call :pedir_fecha
echo.
"%PY%" "%MANAGE%" salidas snapshot %FARG%
echo.
pause
goto menu

:mapa
cls
call :pedir_fecha
echo.
echo  Barriendo TODO el dia en vivo y comparando con la pagina...
echo  (tarda ~1 minuto, no cierres la ventana)
echo.
"%PY%" "%MANAGE%" salidas mapa --detalle %FARG%
echo.
pause
goto menu

:resumen
cls
call :pedir_fecha
echo.
echo  Clasificando TODAS las oficinas del dia en vivo...
echo  (tarda ~1 minuto, no cierres la ventana)
echo.
"%PY%" "%MANAGE%" salidas resumen %FARG%
echo.
pause
goto menu

:mapatodo
cls
call :pedir_fecha
echo.
echo  Barriendo TODO el dia (incluye viajes con precio 0 y reporta
echo  los pares de oficinas que NO respondieron)...
echo  (tarda ~1 minuto, no cierres la ventana)
echo.
"%PY%" "%MANAGE%" salidas mapa --detalle --todo %FARG%
echo.
pause
goto menu
