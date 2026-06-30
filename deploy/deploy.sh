#!/usr/bin/env bash
# Despliegue / actualización de VA-Bus en el servidor.
# Repetible: lo corrés cada vez que actualizás el código.
# Pre-requisitos (ver README-DEPLOY.md): código en /opt/va-bus, .env creado,
# nginx + systemd + cloudflared ya instalados la primera vez.
set -euo pipefail

ROOT=/opt/va-bus
BACK=$ROOT/backend
FRONT=$ROOT/frontend

echo "==> 1/6 Actualizando código (git pull)"
cd "$ROOT" && git pull --ff-only || echo "(sin git o sin cambios, sigo)"

echo "==> 2/6 Backend: venv + dependencias"
cd "$BACK"
[ -d venv ] || python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r "$ROOT/deploy/requirements-prod.txt"

echo "==> 3/6 Migraciones + estáticos"
./venv/bin/python manage.py migrate --noinput
./venv/bin/python manage.py collectstatic --noinput

echo "==> 4/6 Precarga del catálogo de hoy (si falta)"
./venv/bin/python manage.py precargar_rutas --dias 1 --solo-si-falta || true

echo "==> 5/6 Frontend: build"
cd "$FRONT"
pnpm install --frozen-lockfile || pnpm install
# El login con Google necesita el client ID en tiempo de build (Vite). Reusamos
# el mismo GOOGLE_CLIENT_ID que ya está en backend/.env para no duplicarlo.
GOOGLE_CLIENT_ID=$(grep -E '^GOOGLE_CLIENT_ID=' "$BACK/.env" | head -1 | cut -d= -f2- | tr -d '\047"\r ')
if [ -z "$GOOGLE_CLIENT_ID" ]; then
  echo "    (aviso: GOOGLE_CLIENT_ID vacío en backend/.env — el botón de Google no aparecerá)"
fi
VITE_API_URL=https://aerorutasdevenezuela.net/api \
VITE_GOOGLE_CLIENT_ID="$GOOGLE_CLIENT_ID" \
pnpm build

echo "==> 6/6 Reiniciar backend + recargar nginx"
systemctl restart vabus-backend
nginx -t && systemctl reload nginx

echo "==> Listo. https://aerorutasdevenezuela.net"
