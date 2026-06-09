# Despliegue VA-Bus — DigitalOcean + Cloudflare Tunnel + PostgreSQL

Arquitectura (sin abrir puertos):

```
Internet → Cloudflare (HTTPS) → cloudflared (sale del droplet) → nginx :80 (localhost)
   ├── /            → frontend React (dist)
   ├── /api /ws /admin → daphne :5002 (Django)
   └── /static /media  → archivos
                              → PostgreSQL administrada (DO)
```

El droplet solo deja entrar **SSH (22)**. Todo lo demás sale por el túnel.

---

## A) Setup por única vez

### 1. Conectar y preparar el servidor
```bash
ssh root@IP_DEL_DROPLET
apt update && apt upgrade -y
apt install -y python3 python3-venv python3-pip git nginx curl libpq-dev
curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && apt install -y nodejs
npm install -g pnpm
```

### 2. Base de datos administrada
En el panel de DO → base `dbaas-db-1243321`:
- **Settings → Trusted Sources**: agregá el droplet `va-bus-produccion`.
- Usá el host de **VPC network** si ambos están en la misma VPC.

### 3. Código + .env
```bash
cd /opt && git clone TU_REPO va-bus
cp /opt/va-bus/deploy/.env.production.example /opt/va-bus/backend/.env
nano /opt/va-bus/backend/.env       # rellenar secretos (DB, SECRET_KEY, etc.)
```
Generar SECRET_KEY:
```bash
python3 -c "import secrets;print(secrets.token_urlsafe(64))"
```

### 4. systemd + nginx
```bash
cp /opt/va-bus/deploy/vabus-backend.service /etc/systemd/system/
cp /opt/va-bus/deploy/nginx-vabus.conf /etc/nginx/sites-available/vabus
ln -sf /etc/nginx/sites-available/vabus /etc/nginx/sites-enabled/vabus
rm -f /etc/nginx/sites-enabled/default
systemctl daemon-reload
systemctl enable vabus-backend
```

### 5. Primer despliegue
```bash
chmod +x /opt/va-bus/deploy/deploy.sh
/opt/va-bus/deploy/deploy.sh
# Crear admin (una vez):
cd /opt/va-bus/backend && ./venv/bin/python manage.py createsuperuser
```

### 6. Cloudflare Tunnel
En Cloudflare → **Zero Trust → Networks → Tunnels → Create a tunnel** (Cloudflared).
Copiá el token y en el droplet:
```bash
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb -o cloudflared.deb
dpkg -i cloudflared.deb
cloudflared service install TU_TOKEN
```
En el panel del túnel, **Public Hostnames**:
- `aerorutasdevenezuela.net` → `http://localhost:80`
- (opcional) `app.aerorutasdevenezuela.net` → `http://localhost:80`

Cloudflare crea el DNS automáticamente.

### 7. Cron para la precarga del catálogo
```bash
crontab -e
```
```
0 */6 * * * cd /opt/va-bus/backend && venv/bin/python manage.py precargar_rutas --dias 1 --solo-si-falta >> /opt/va-bus/backend/precargar_rutas.log 2>&1
```

---

## B) Actualizar (cada vez que cambia el código)
```bash
/opt/va-bus/deploy/deploy.sh
```

## C) Verificar / diagnosticar
```bash
systemctl status vabus-backend      # backend corriendo
journalctl -u vabus-backend -n 50   # logs del backend
nginx -t                            # config nginx OK
cloudflared tunnel info             # estado del túnel
```
- Web: `https://aerorutasdevenezuela.net`
- API: `https://aerorutasdevenezuela.net/api/aerorutas/oficinas/`
- Admin: `https://aerorutasdevenezuela.net/admin/`

## D) App móvil (APK)
```bash
flutter build apk --release --dart-define=API_BASE_URL=https://aerorutasdevenezuela.net/api
```

## Notas
- **R4 / Mibanco**: dales la IP pública del droplet para el whitelist (las llamadas salientes salen desde esa IP).
- `InMemoryChannelLayer` funciona con **un** proceso daphne. Si escalás a varios, pasar a Redis.
- Cuando termines de probar, **rotá** la password de la DB que quedó en el chat.
