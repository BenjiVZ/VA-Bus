# 🚍 VA-Bus — Sistema de Reservas de Pasajes

Sistema web de reservas de boletos para la empresa **Aerorutas** (Venezuela), con backend Django REST y frontend React + Vite.

---

## 📁 Estructura del Proyecto

```
VA-Bus/
├── backend/          # API REST — Django + DRF
│   ├── config/       # Settings, URLs raíz, WSGI/ASGI
│   ├── api_externa/  # Integración con APIs externas
│   ├── pagos/        # Módulo de pagos y comprobantes
│   ├── reservas/     # Lógica de reservas de asientos
│   ├── usuarios/     # Auth, perfiles, Google OAuth
│   ├── viajes/       # Viajes, buses, rutas, layouts
│   └── scripts/      # Seeds, resets y utilidades
├── frontend/         # SPA — React + Vite
│   └── src/
│       ├── components/  # Componentes reutilizables
│       ├── pages/       # Vistas/páginas
│       ├── styles/      # CSS por página/componente
│       ├── services/    # Capa de API (axios)
│       └── context/     # React Context (Auth)
├── docs/             # Documentación, logos, marketing
│   ├── logos/
│   ├── diagramas/
│   ├── marketing/
│   ├── presentacion/
│   └── fotos_vehiculos/
└── ejecutar.bat      # Inicia backend + frontend + navegador
```

---

## 🚀 Inicio Rápido

### Opción 1: Script automático (Windows)
```bat
ejecutar.bat
```

### Opción 2: Manual

**Backend:**
```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 8001
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev -- --host
```

---

## 🔗 URLs

| Servicio  | URL                        |
|-----------|----------------------------|
| Frontend  | http://localhost:3000       |
| Backend   | http://localhost:8001       |
| Admin     | http://localhost:8001/admin |

---

## ⚙️ Variables de Entorno

Crear `backend/.env` con:

```env
SECRET_KEY=...
DEBUG=True
GOOGLE_CLIENT_ID=...
```

---

## 📌 Tecnologías

- **Backend:** Python 3.x, Django 5.x, Django REST Framework
- **Frontend:** React 18, Vite, React Router
- **Auth:** JWT + Google OAuth 2.0
- **DB:** SQLite (dev) / SQL Server (prod)
