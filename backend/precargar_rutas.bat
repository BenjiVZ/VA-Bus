@echo off
REM Asegura el catalogo de viajes de Aerorutas para HOY.
REM Con --solo-si-falta: si HOY ya tiene catalogo, sale al instante (chequeo
REM barato de BD); solo hace el barrido cuando falta (dia nuevo o fallo previo).
REM Aerorutas solo publica las rutas del dia, por eso --dias 1.
REM Pensado para correr seguido (cada hora) via Programador de tareas sin pesar.
cd /d "%~dp0"
venv\Scripts\python.exe manage.py precargar_rutas --dias 1 --solo-si-falta >> precargar_rutas.log 2>&1
