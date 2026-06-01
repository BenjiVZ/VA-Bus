# Aerorutas — App (Flutter)

App de clientes de Aerorutas de Venezuela. **Multi-plataforma**: Android, iOS y **Web** (para preview/testing rápido sin instalar nada). Consume el mismo backend Django REST que el frontend principal.

## Pantallas

- Home (búsqueda + rutas + estadísticas)
- Login / Registro / Verificar email / Recuperar contraseña
- Lista de viajes con filtros
- Selección de asientos (mapa con layout JSON del PisoAutobus, lock temporal de 2 min)
- Pago (métodos configurables, copia de datos, subida de comprobante + foto del billete si aplica)
- Confirmación de envío
- Mis reservas (agrupadas por compra)
- Ticket con QR (resuelve `/verificar/<codigo>`)
- Perfil (editar nombre, cédula, teléfono; logout)

## Stack

- Flutter 3.38 · Dart 3.10
- Provider para estado
- Dio para HTTP (con refresh-token automático)
- flutter_secure_storage para tokens JWT
- go_router para navegación
- qr_flutter para tickets QR
- image_picker para subir comprobantes

## Estructura

```
mobile/
├── lib/
│   ├── main.dart
│   ├── app.dart
│   ├── config/        # constants, theme, router
│   ├── models/        # usuario, viaje, reserva, metodo_pago
│   ├── services/      # storage, api_client, auth, viajes, reservas, pagos
│   ├── providers/     # AuthProvider
│   ├── screens/       # auth/, home/, viajes/, pago/, reservas/, perfil/
│   └── widgets/       # seat_map, app_logo
├── android/
└── ios/
```

## Setup

```bash
cd mobile
flutter pub get
```

## Variables de entorno

Se pasan vía `--dart-define` al ejecutar/compilar.

| Variable          | Default                          | Descripción                                  |
| ----------------- | -------------------------------- | -------------------------------------------- |
| `API_BASE_URL`    | `http://10.0.2.2:5002/api`       | URL del backend (con /api al final).         |
| `GOOGLE_CLIENT_ID`| `''`                             | Reservado para futura integración OAuth.     |

### Backend según el target

| Target              | API_BASE_URL                                                |
| ------------------- | ----------------------------------------------------------- |
| Emulador Android    | `http://10.0.2.2:5002/api`                                  |
| Simulador iOS       | `http://localhost:5002/api`                                 |
| Dispositivo físico  | `http://<IP-de-tu-PC-en-la-LAN>:5002/api`                   |
| Producción          | `https://ardvb.aplicacionesdamasco.com/api`                 |

> El backend debe estar corriendo: `cd backend && python manage.py runserver 0.0.0.0:5002` (el `0.0.0.0` es necesario si lo usas desde un dispositivo físico).

## Ejecutar en desarrollo

> **Tip:** el default de `API_BASE_URL` se detecta automático por plataforma (`localhost:5002` en web/iOS/desktop, `10.0.2.2:5002` en emulador Android). Solo necesitas el flag `--dart-define=API_BASE_URL=...` para dispositivos físicos o producción.

### 🌐 Web (más rápido para probar — recomendado)

Antes de arrancar la app, asegúrate que el backend Django esté corriendo:

```bash
cd backend
python manage.py runserver 5002
```

Luego, desde `mobile/`:

```bash
flutter run -d chrome --web-port=3001
```

Abre automáticamente Chrome en `http://localhost:3001`. Hot reload con `r`, restart con `R`, quit con `q`.

> **Importante:** el navegador hace peticiones desde `localhost:3001` al backend en `localhost:5002`. Esto es **cross-origin** pero ya está permitido porque `settings.py` tiene `CORS_ALLOW_ALL_ORIGINS = True` en modo dev.

También funciona en Edge: `flutter run -d edge --web-port=3001`.

### Android (emulador)

```bash
flutter run
```

### iOS (simulador, requiere macOS)

```bash
flutter run
```

### Dispositivo físico

Conecta el teléfono y ejecuta:

```bash
flutter run --dart-define=API_BASE_URL=http://192.168.1.X:5002/api
```

(reemplaza `192.168.1.X` por la IP real de tu PC).

## Build de release

### 🌐 Web (estático, para hostear con cualquier server)

```bash
flutter build web --release \
  --dart-define=API_BASE_URL=https://ardvb.aplicacionesdamasco.com/api
```

Genera la carpeta `build/web/` con el bundle estático. Puedes subirla a Nginx, GitHub Pages, Netlify, Vercel o servirla con `python -m http.server` para probar.

### Android APK

```bash
flutter build apk --release \
  --dart-define=API_BASE_URL=https://ardvb.aplicacionesdamasco.com/api
```

El APK queda en `build/app/outputs/flutter-apk/app-release.apk`.

### Android AAB (Play Store)

```bash
flutter build appbundle --release \
  --dart-define=API_BASE_URL=https://ardvb.aplicacionesdamasco.com/api
```

### iOS (requiere macOS + Xcode + Apple Developer)

```bash
flutter build ios --release \
  --dart-define=API_BASE_URL=https://ardvb.aplicacionesdamasco.com/api
```

Luego abre `ios/Runner.xcworkspace` en Xcode y archiva.

## Paleta (de frontend/src/styles/base.css)

- **Navy** `#1A3A6B` · hover `#142E55` · dark `#0E2240`
- **Amarillo dorado del logo** `#F5C842` · `#E8A820` · `#D49A10`
- **Rojo acento** `#C62828`
- **Verde éxito** `#00875A`
- **Tipografía** Inter (cargada vía google_fonts)

## Pendiente

- Reemplazar el logo placeholder (`AppLogo` en `lib/widgets/app_logo.dart`) por el real en `assets/logo/aerorutas.png`.
- Google Sign-In móvil (paquete `google_sign_in` + Client ID nativo Android/iOS).
- Documentos para menores / mascota / discapacidad en el flujo de reserva.
- Push notifications (FCM) para validación de comprobante.
