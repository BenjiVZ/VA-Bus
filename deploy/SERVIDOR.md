# 🖥️ Servidor de producción — VA-Bus (Aerorutas de Venezuela)

Documentación operativa del despliegue. **No contiene contraseñas** (viven en
`/opt/va-bus/backend/.env` del servidor y en el panel de DigitalOcean).

---

## 1. Accesos rápidos

| Qué | Dónde |
|---|---|
| **Sitio web** | https://aerorutasdevenezuela.net |
| **Admin Django** | https://aerorutasdevenezuela.net/admin/ (usuario `admin`) |
| **API** | https://aerorutasdevenezuela.net/api/ |
| **SSH al servidor** | `ssh root@164.90.148.65` |
| **Panel droplet** | DigitalOcean → Droplets → `va-bus-produccion` |
| **Panel base de datos** | DigitalOcean → Databases → `dbaas-db-1243321` |
| **Túnel** | Cloudflare → Zero Trust → Networks → Tunnels → `va-bus` |
| **DNS / dominio** | Cloudflare → `aerorutasdevenezuela.net` |

---

## 2. Acceso por SSH

```bash
ssh root@164.90.148.65
```
- Usuario: `root`
- Contraseña: la que definiste (autenticación por contraseña habilitada).

### Si olvidás la contraseña
1. Panel DO → droplet `va-bus-produccion` → **Access → Reset Root Password** (llega por email).
2. El **primer login** obliga a cambiarla. ⚠️ El cliente SSH de Windows (PowerShell)
   **falla** en ese cambio forzado — usá **Git Bash** o la **consola web** de DO
   (Access → Launch Droplet Console) para hacer el cambio. Después PowerShell ya entra normal.

> **IP pública (egress):** `164.90.148.65` — es la que sale a internet (la que hay que
> dar a Mibanco para el whitelist de R4). Verificable en el server con `curl https://api.ipify.org`.

---

## 3. Infraestructura

```
Internet
   │  HTTPS (lo pone Cloudflare)
   ▼
Cloudflare  ──►  cloudflared (túnel, SALE del droplet, sin puertos abiertos)
   │
   ▼
nginx :80 (solo localhost)
   ├── /            → frontend React  (/opt/va-bus/frontend/dist)
   ├── /api  /ws  /admin → daphne 127.0.0.1:5002 (Django)
   └── /static  /media  → archivos en disco
                  │
                  ▼
        PostgreSQL administrada (DigitalOcean)
```

- **Droplet:** `va-bus-produccion` · Ubuntu 24.04 LTS · 2 GB RAM · 70 GB · región SFO3.
- **Firewall:** solo entra **SSH (22)**. Todo lo demás sale por el túnel (no hay puertos web abiertos).
- **Zona horaria:** `America/Caracas` (crítico — ver sección 8).
- **Código:** `/opt/va-bus` (repo `github.com/BenjiVZ/VA-Bus`, rama `main`).

---

## 4. Base de datos (PostgreSQL administrada)

| Dato | Valor |
|---|---|
| Cluster | `dbaas-db-1243321` (PostgreSQL 18, SFO3) |
| Host | `dbaas-db-1243321-do-user-35115103-0.i.db.ondigitalocean.com` |
| Puerto | `25060` |
| Base | `defaultdb` |
| Usuario | `doadmin` |
| SSL | `require` |
| **Contraseña** | en `/opt/va-bus/backend/.env` (`DB_PASSWORD`) — **NUNCA en git** |

- El droplet está autorizado en **Network Access → Trusted Sources**.
- Django usa Postgres automáticamente porque `DB_HOST` está definido en el `.env`
  (si no estuviera, caería a SQLite).

> ⚠️ **Pendiente de seguridad:** rotar `DB_PASSWORD` desde el panel de DO (quedó expuesta
> en el chat de configuración). Tras rotarla: actualizar el `.env` y `systemctl restart vabus-backend`.

---

## 5. Servicios (systemd)

### Backend — `vabus-backend`
Corre daphne (ASGI) en `127.0.0.1:5002`. Arranca solo al bootear.
```bash
systemctl status vabus-backend          # estado
systemctl restart vabus-backend         # reiniciar (tras cambios de backend/.env)
journalctl -u vabus-backend -n 50 --no-pager   # logs
```
- Unit: `/etc/systemd/system/vabus-backend.service`
- Lee variables de `/opt/va-bus/backend/.env`

### Túnel — `cloudflared`
Conecta el dominio con el server. Arranca solo.
```bash
systemctl status cloudflared
journalctl -u cloudflared -n 30 --no-pager
```
- Túnel Cloudflare: **`va-bus`** (ID `fe768ee5-3ef7-48e1-81b3-687d986c1e48`).
- **Forzado a protocolo `http2`** (override en
  `/etc/systemd/system/cloudflared.service.d/protocol.conf`) porque QUIC daba problemas.
- Public Hostname configurado en el panel: `aerorutasdevenezuela.net` → `http://localhost:80`.

### Web server — `nginx`
```bash
nginx -t                  # validar config
systemctl reload nginx    # aplicar cambios
```
- Config: `/etc/nginx/sites-available/vabus` (symlink en `sites-enabled/`).
- Sirve el frontend (`dist`), proxea `/api` `/ws` `/admin` a daphne, y `/static` `/media`.

---

## 6. Catálogo de viajes (cron)

Los viajes vienen del sistema externo **Aerorutas** y se precargan en la BD por día.
```bash
crontab -l    # ver el cron
```
Cron actual (cada 6 h, hora de Venezuela):
```
0 */6 * * * cd /opt/va-bus/backend && venv/bin/python manage.py precargar_rutas --dias 1 --solo-si-falta >> /opt/va-bus/backend/precargar_rutas.log 2>&1
```
- `--solo-si-falta`: si HOY ya tiene catálogo, no hace nada (chequeo barato).
- Forzar carga manual de hoy:
  ```bash
  cd /opt/va-bus/backend && source venv/bin/activate
  python manage.py precargar_rutas --dias 1
  ```
- Log: `/opt/va-bus/backend/precargar_rutas.log`

---

## 7. Desplegar / actualizar (cuando cambia el código)

1. En tu PC: `git push origin main`.
2. En el servidor, **una de dos**:

   **Opción A — script todo-en-uno:**
   ```bash
   bash /opt/va-bus/deploy/deploy.sh
   ```
   (git pull + deps + migrate + rebuild frontend + restart backend + reload nginx)

   **Opción B — manual:**
   ```bash
   cd /opt/va-bus && git pull
   # si cambió el frontend:
   cd frontend && VITE_API_URL=https://aerorutasdevenezuela.net/api pnpm build
   # si cambió el backend:
   systemctl restart vabus-backend
   # si hubo migraciones nuevas:
   cd /opt/va-bus/backend && source venv/bin/activate && python manage.py migrate
   ```
3. En el navegador: **Ctrl+Shift+R** (refresco fuerte).

> `migrate` solo aplica cambios de esquema nuevos; **no borra datos**. Re-desplegar es seguro.

---

## 8. Zona horaria (¡importante!)

El servidor **debe** estar en `America/Caracas`:
```bash
timedatectl set-timezone America/Caracas
systemctl restart vabus-backend
```
**Por qué:** Aerorutas solo publica las rutas de "hoy" en hora de Venezuela. Si el server
queda en UTC, de noche `date.today()` se adelanta un día y el catálogo (y los contadores
del home) salen vacíos/0. **Si se recrea el droplet, repetir este ajuste.**

---

## 9. Admin de Django

- URL: **https://aerorutasdevenezuela.net/admin/**
- Usuario: `admin` (superuser creado en el deploy).
- Crear otro superuser:
  ```bash
  cd /opt/va-bus/backend && source venv/bin/activate
  python manage.py createsuperuser
  ```

---

## 10. Pasarela de pago R4 (Mibanco)

- Método: **Débito Inmediato OTP** (`GenerarOtp` → `DebitoInmediato` → si `AC00`, `ConsultarOperaciones`).
- Código en `backend/r4conecta/`. Credenciales (`R4_COMMERCE_TOKEN`) en el `.env`.
- **Requisito del banco:** Mibanco debe agregar la IP **`164.90.148.65`** a su lista blanca
  para que las llamadas salientes (server → banco) no sean bloqueadas por su WAF.
- Endpoints de prueba (`/api/r4/test/`) quedan **deshabilitados** en producción (`DEBUG=False`).

---

## 11. Troubleshooting rápido

| Síntoma | Revisar |
|---|---|
| El sitio no carga | `systemctl status cloudflared` y `systemctl status nginx` |
| Error 502 en el sitio | `systemctl status vabus-backend` + `journalctl -u vabus-backend -n 50` |
| El admin se ve sin estilos | `python manage.py collectstatic --noinput` (en venv) |
| Home en 0 / sin viajes | Zona horaria (sección 8) + `precargar_rutas --dias 1` |
| Túnel caído | `journalctl -u cloudflared -n 30` (ver que use http2) |
| No conecta a la BD | Trusted Sources en DO + datos del `.env` |

### Comandos útiles
```bash
curl https://api.ipify.org                                   # IP de salida real
curl http://127.0.0.1:5002/api/aerorutas/oficinas/           # backend directo
curl -H "Host: aerorutasdevenezuela.net" http://127.0.0.1/   # nginx → frontend
date                                                          # confirmar hora Venezuela
```

---

## 12. Secretos y dónde viven

| Secreto | Ubicación | Nota |
|---|---|---|
| `SECRET_KEY` Django | `/opt/va-bus/backend/.env` | — |
| `DB_PASSWORD` | `.env` + panel DO | **rotar** (quedó en chat) |
| `R4_COMMERCE_TOKEN` | `.env` | del banco |
| `AERORUTAS_API_TOKEN` | `.env` | del sistema externo |
| Token del túnel | dentro del unit de `cloudflared` | re-generable en Cloudflare |
| Contraseña root SSH | solo en tu poder | reseteable en panel DO |

El `.env` está en `.gitignore` (nunca se versiona). Para ver/editar:
```bash
nano /opt/va-bus/backend/.env
# tras editar:
systemctl restart vabus-backend
```
