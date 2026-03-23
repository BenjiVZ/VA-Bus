@echo off
title VA-Bus — Iniciando Sistema
color 0A

echo ============================================
echo        VA-Bus — Sistema de Reservas
echo ============================================
echo.

:: Iniciar Backend (Django)
echo [1/3] Iniciando Backend (Django en puerto 8001)...
start "VA-Bus Backend" cmd /k "cd /d %~dp0backend && python manage.py runserver 8001"

:: Esperar a que Django arranque
timeout /t 3 /nobreak >nul

:: Iniciar Frontend (React/Vite)
echo [2/3] Iniciando Frontend (Vite en puerto 3000)...
start "VA-Bus Frontend" cmd /k "cd /d %~dp0frontend && npm run dev -- --host"

:: Esperar a que Vite arranque
timeout /t 4 /nobreak >nul

:: Abrir navegador
echo [3/3] Abriendo navegador...
start http://localhost:3000

echo.
echo ============================================
echo   Sistema iniciado correctamente!
echo   Frontend: http://localhost:3000
echo   Backend:  http://localhost:8001
echo   Admin:    http://localhost:8001/admin
echo ============================================
echo.
echo Cierra esta ventana cuando quieras detener todo.
pause
