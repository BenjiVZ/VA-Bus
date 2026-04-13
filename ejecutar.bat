@echo off
title VA-Bus — Iniciando Sistema
color 0A

echo ============================================
echo        VA-Bus — Sistema de Reservas
echo ============================================
echo.

:: Iniciar Backend (Django en puerto 3000)
echo [1/3] Iniciando Backend (Django en puerto 3000)...
start "VA-Bus Backend" cmd /k "cd /d %~dp0backend && python manage.py runserver 3000"

:: Esperar a que Django arranque
timeout /t 3 /nobreak >nul

:: Iniciar Frontend (React/Vite en puerto 3001)
echo [2/3] Iniciando Frontend (Vite en puerto 3001)...
start "VA-Bus Frontend" cmd /k "cd /d %~dp0frontend && npm run dev -- --host"

:: Esperar a que Vite arranque
timeout /t 4 /nobreak >nul

:: Abrir navegador
echo [3/3] Abriendo navegador...
start http://localhost:3001

echo.
echo ============================================
echo   Sistema iniciado correctamente!
echo   Backend:  http://localhost:3000  (backend.aplicacionesdamasco.com)
echo   Frontend: http://localhost:3001  (frontend.aplicacionesdamasco.com)
echo   Admin:    http://localhost:3000/admin
echo ============================================
echo.
echo Cierra esta ventana cuando quieras detener todo.
pause
