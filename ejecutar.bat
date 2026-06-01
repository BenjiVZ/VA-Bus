@echo off
title VA-Bus — Iniciando Sistema
color 0A

echo ============================================
echo        VA-Bus — Sistema de Reservas
echo ============================================
echo.

:: Liberar puertos si estan ocupados
echo [0/3] Liberando puertos 5001 y 5002...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5001 ^| findstr LISTENING 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :5002 ^| findstr LISTENING 2^>nul') do (
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 2 /nobreak >nul

:: Iniciar Backend (Django + Channels via Daphne en puerto 5002)
:: Daphne es un servidor ASGI que soporta HTTP + WebSockets en el mismo puerto.
:: Las URLs REST siguen funcionando exactamente igual, y se agregan rutas WS en /ws/...
echo [1/3] Iniciando Backend (Daphne ASGI en puerto 5002)...
start "VA-Bus Backend" cmd /k "cd /d %~dp0backend && venv\Scripts\daphne.exe -b 0.0.0.0 -p 5002 config.asgi:application"

:: Esperar a que Django arranque
timeout /t 3 /nobreak >nul

:: Iniciar Frontend (React/Vite en puerto 5001)
echo [2/3] Iniciando Frontend (Vite en puerto 5001)...
start "VA-Bus Frontend" cmd /k "cd /d %~dp0frontend && pnpm run dev -- --host"

:: Esperar a que Vite arranque
timeout /t 4 /nobreak >nul

:: Abrir navegador
echo [3/3] Abriendo navegador...
start http://localhost:5001

echo.
echo ============================================
echo   Sistema iniciado correctamente!
echo   Backend:  http://localhost:5002  (ardvb.aplicacionesdamasco.com)
echo   Frontend: http://localhost:5001  (ardvf.aplicacionesdamasco.com)
echo   Admin:    http://localhost:5002/admin
echo ============================================
echo.
echo Cierra esta ventana cuando quieras detener todo.
pause
