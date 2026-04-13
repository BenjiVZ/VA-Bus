# Frontend VA-Bus (React + Vite)

## Configuración de entorno

1. Crea tu archivo local de entorno:

```bash
cp .env.example .env
```

2. Configura estas variables:

- `VITE_API_URL`: URL base de la API (incluyendo `/api`).
	- Ejemplo local: `http://localhost:8001/api`
- `VITE_GOOGLE_CLIENT_ID`: Client ID de Google OAuth para login social.

## Scripts

- `npm run dev` → Desarrollo
- `npm run build` → Build producción
- `npm run preview` → Vista previa del build

## Notas

- Las rutas de imágenes (ej. comprobantes) se resuelven desde `VITE_API_URL`, evitando hardcodes por puerto.
- No subas tu archivo `.env` al repositorio.
