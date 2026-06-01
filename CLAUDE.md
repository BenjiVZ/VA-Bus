# CLAUDE.md — VA-Bus (Aerorutas de Venezuela)

Guía para agentes que trabajan en este repositorio.

## ⚠️ Reglas obligatorias

- **Usa SIEMPRE `pnpm` para el frontend** (nunca `npm` ni `yarn`). Instalar, agregar paquetes,
  scripts, todo con pnpm:
  - Instalar dependencias: `pnpm --dir frontend install`
  - Build: `pnpm --dir frontend build`
  - Dev: `pnpm --dir frontend dev`
  - Agregar paquete: `pnpm --dir frontend add <paquete>`
  - Si hay que regenerar el lockfile, que sea `pnpm-lock.yaml` (no `package-lock.json`).

## Estructura del proyecto

Monorepo con tres aplicaciones que comparten el mismo backend:

```
VA-Bus/
├── backend/    Django 5.2 + DRF + Channels (API REST + WebSockets)
├── frontend/   React 19 + Vite (SPA web pública + panel admin)  ← pnpm
├── mobile/     Flutter (app Android/iOS + web)
└── docs/       logos, marketing, presentación, presupuestos
```

## Comandos por app

### Frontend (`frontend/`) — React + Vite
- Gestor de paquetes: **pnpm** (obligatorio).
- `pnpm --dir frontend install` · `pnpm --dir frontend build` · `pnpm --dir frontend dev`

### Backend (`backend/`) — Django
- Entorno virtual en `backend/venv/`.
- Instalar: `backend\venv\Scripts\python.exe -m pip install -r backend\requirements.txt`
- Verificar: `backend\venv\Scripts\python.exe backend\manage.py check`
- Migrar: `... manage.py migrate`
- Arrancar (con WebSockets, vía ASGI/daphne): `... manage.py runserver 8001`
- Requiere variables de entorno en `backend/.env` (`SECRET_KEY`, `GOOGLE_CLIENT_ID`,
  `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EXTERNAL_API_KEY`).

### Mobile (`mobile/`) — Flutter
- Requiere Flutter con Dart `^3.10.8` (Flutter 3.44+).
- Dependencias: `flutter pub get --directory mobile`
- Compilar APK: `cd mobile && flutter build apk --release`

## Notas

- El backend usa SQLite en desarrollo. Web y móvil consumen la misma API
  (`*.aplicacionesdamasco.com` en producción).
- No versionar secretos ni datos: `backend/.env`, `backend/db.sqlite3`,
  `backend/media/` y los `__pycache__/` no deberían estar en git.
