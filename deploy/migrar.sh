#!/usr/bin/env bash
# Actualiza el backend y aplica migraciones AUTOMATICAMENTE.
# Uso en el servidor:  bash /opt/va-bus/deploy/migrar.sh
#
# Hace: git pull -> migrate -> collectstatic -> reiniciar backend.
# Es idempotente: si no hay migraciones nuevas, migrate no hace nada.
# Para el deploy COMPLETO (incluye build del frontend) usa deploy.sh.
set -euo pipefail

ROOT=/opt/va-bus
BACK=$ROOT/backend
PY=$BACK/venv/bin/python

echo "==> 1/4 Actualizando codigo (git pull)"
cd "$ROOT"
git pull --ff-only

echo "==> 2/4 Aplicando migraciones"
cd "$BACK"
"$PY" manage.py migrate --noinput

echo "==> 3/4 Recolectando estaticos"
"$PY" manage.py collectstatic --noinput

echo "==> 4/4 Reiniciando backend"
systemctl restart vabus-backend

echo "==> Listo. https://aerorutasdevenezuela.net"
