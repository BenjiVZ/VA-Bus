# API Externa — Aerorutas de Venezuela

## Documentación de Integración para Sistema de Control

**Versión:** 1.0  
**Fecha:** Abril 2026  
**Base URL:** `http://tu-servidor.com/api/externo/`

---

## Autenticación

Todas las peticiones deben incluir el header:

```
X-API-KEY: <clave_proporcionada>
```

**Ejemplo:**
```bash
curl -H "X-API-KEY: cU3g7kZWiFR4r1qYxjWEA89pL_awvhMI..." \
     http://localhost:8001/api/externo/viajes/
```

**Errores de autenticación:**
| Código | Significado |
|--------|-------------|
| 401 | API Key no proporcionada o inválida |
| 429 | Límite de peticiones excedido (máx 30/min) |

---

## ENDPOINTS QUE USTEDES CONSUMEN (leer datos)

### 1. Listar Viajes Activos

```
GET /api/externo/viajes/
```

**Parámetros de consulta (opcionales):**
| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| `fecha_desde` | `YYYY-MM-DD` | Filtrar desde esta fecha |
| `fecha_hasta` | `YYYY-MM-DD` | Filtrar hasta esta fecha |
| `ruta_origen` | `string` | Filtrar por ciudad de origen |
| `ruta_destino` | `string` | Filtrar por ciudad de destino |

**Ejemplo de petición:**
```bash
GET /api/externo/viajes/?fecha_desde=2026-04-05&ruta_origen=Caracas
```

**Respuesta exitosa (200):**
```json
{
  "total": 2,
  "viajes": [
    {
      "id": 15,
      "ruta": {
        "id": 3,
        "origen": "Caracas",
        "destino": "Maracaibo",
        "duracion_estimada": "12 horas"
      },
      "autobus": {
        "id": 1,
        "nombre": "Ejecutivo Premium",
        "placa": "AB123CD",
        "pisos": 2
      },
      "tipo_viaje": "ida",
      "fecha_salida": "2026-04-10",
      "hora_salida": "22:00:00",
      "fecha_vuelta": null,
      "hora_vuelta": null,
      "precio_usd": 45.00,
      "asientos_totales": 42,
      "asientos_ocupados": 15,
      "asientos_disponibles": 27
    }
  ],
  "timestamp": "2026-04-02T20:30:00.000000-04:00"
}
```

---

### 2. Detalle de un Viaje

```
GET /api/externo/viajes/{id}/
```

**Respuesta exitosa (200):**
```json
{
  "id": 15,
  "ruta": {
    "id": 3,
    "origen": "Caracas",
    "destino": "Maracaibo",
    "duracion_estimada": "12 horas"
  },
  "autobus": {
    "id": 1,
    "nombre": "Ejecutivo Premium",
    "placa": "AB123CD",
    "marca": "Mercedes-Benz",
    "color": "Blanco",
    "anio": 2022,
    "pisos": 2,
    "capacidad_total": 42
  },
  "tipo_viaje": "ida",
  "fecha_salida": "2026-04-10",
  "hora_salida": "22:00:00",
  "fecha_vuelta": null,
  "hora_vuelta": null,
  "precio_usd": 45.00,
  "asientos_totales": 42,
  "asientos_ocupados": 15,
  "asientos_disponibles": 27,
  "timestamp": "2026-04-02T20:30:00.000000-04:00"
}
```

---

### 3. Mapa de Asientos (con estado y datos de pasajero)

```
GET /api/externo/viajes/{id}/asientos/
```

**Respuesta exitosa (200):**
```json
{
  "viaje_id": 15,
  "autobus": "Ejecutivo Premium",
  "placa": "AB123CD",
  "asientos_totales": 42,
  "asientos_ocupados": 15,
  "asientos_disponibles": 27,
  "pisos": [
    {
      "piso": 1,
      "filas": 10,
      "columnas": 5,
      "asientos": [
        {
          "numero": 1,
          "piso": 1,
          "estado": "disponible"
        },
        {
          "numero": 2,
          "piso": 1,
          "estado": "confirmado",
          "pasajero": {
            "nombre": "Juan Pérez",
            "cedula": "V-12345678",
            "es_menor": false
          }
        },
        {
          "numero": 3,
          "piso": 1,
          "estado": "pendiente"
        },
        {
          "numero": 4,
          "piso": 1,
          "estado": "apartado"
        }
      ]
    },
    {
      "piso": 2,
      "filas": 10,
      "columnas": 4,
      "asientos": [
        {
          "numero": 21,
          "piso": 2,
          "estado": "disponible"
        }
      ]
    }
  ],
  "timestamp": "2026-04-02T20:30:00.000000-04:00"
}
```

**Estados posibles de un asiento:**
| Estado | Significado |
|--------|-------------|
| `disponible` | Libre para ser reservado |
| `pendiente` | Reservado temporalmente (expira en 15 min) |
| `apartado` | Pago en proceso de verificación |
| `confirmado` | Pagado y confirmado |

> **Nota:** Los datos del pasajero (`nombre`, `cedula`) solo se incluyen en asientos con estado `confirmado`.

---

### 4. Lista de Pasajeros Confirmados

```
GET /api/externo/viajes/{id}/pasajeros/
```

**Respuesta exitosa (200):**
```json
{
  "viaje_id": 15,
  "ruta": "Caracas → Maracaibo",
  "fecha_salida": "2026-04-10",
  "hora_salida": "22:00:00",
  "total_pasajeros": 15,
  "pasajeros": [
    {
      "asiento": 2,
      "piso": 1,
      "nombre": "Juan Pérez",
      "cedula": "V-12345678",
      "es_menor": false,
      "codigo_ticket": "A1B2C3D4",
      "fecha_confirmacion": "2026-04-01T15:30:00.000000-04:00"
    },
    {
      "asiento": 5,
      "piso": 1,
      "nombre": "María García (Menor)",
      "cedula": "V-87654321",
      "es_menor": true,
      "codigo_ticket": "E5F6G7H8",
      "fecha_confirmacion": "2026-04-01T16:00:00.000000-04:00"
    }
  ],
  "timestamp": "2026-04-02T20:30:00.000000-04:00"
}
```

---

## ENDPOINTS QUE USTEDES ENVIAN (escribir datos)

### 5. Registrar Asientos Ocupados Externamente

```
POST /api/externo/viajes/{id}/ocupar-asientos/
```

Use este endpoint para informar al sistema de Aerorutas que asientos fueron vendidos/ocupados a través de su sistema. Los asientos se marcan como **confirmados** directamente.

**Body JSON requerido:**
```json
{
  "asientos": [
    {
      "numero": 5,
      "piso": 1,
      "nombre_pasajero": "Pedro López",
      "cedula_pasajero": "V-15678901"
    },
    {
      "numero": 6,
      "piso": 1,
      "nombre_pasajero": "Ana Rodríguez",
      "cedula_pasajero": "V-20345678"
    }
  ],
  "referencia_externa": "TICKET-EXT-2026-001"
}
```

**Campos por asiento:**
| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `numero` | `integer` | Si | Numero del asiento |
| `piso` | `integer` | No (default: 1) | Piso del autobus |
| `nombre_pasajero` | `string` | Si | Nombre completo del pasajero |
| `cedula_pasajero` | `string` | Si | Cedula de identidad (ej: "V-12345678") |

**Campo adicional:**
| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| `referencia_externa` | `string` | No | ID o referencia de su sistema para trazabilidad |

**Respuesta exitosa (201):**
```json
{
  "mensaje": "2 asiento(s) registrado(s) exitosamente.",
  "referencia_externa": "TICKET-EXT-2026-001",
  "grupo_pago": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "asientos_creados": [
    {
      "reserva_id": 45,
      "asiento": 5,
      "piso": 1,
      "codigo_ticket": "X1Y2Z3W4",
      "nombre": "Pedro López",
      "cedula": "V-15678901"
    },
    {
      "reserva_id": 46,
      "asiento": 6,
      "piso": 1,
      "codigo_ticket": "M5N6O7P8",
      "nombre": "Ana Rodríguez",
      "cedula": "V-20345678"
    }
  ],
  "errores": null,
  "timestamp": "2026-04-02T20:30:00.000000-04:00"
}
```

**Respuesta con errores parciales (201):**
```json
{
  "mensaje": "1 asiento(s) registrado(s) exitosamente.",
  "referencia_externa": "TICKET-EXT-2026-002",
  "grupo_pago": "...",
  "asientos_creados": [
    { "reserva_id": 47, "asiento": 10, "piso": 1, "codigo_ticket": "...", "nombre": "...", "cedula": "..." }
  ],
  "errores": [
    "Asiento #2 (Piso 1, Asiento 5): ya está ocupado."
  ],
  "timestamp": "..."
}
```

**Límites:**
- Máximo **50 asientos** por petición.
- Los asientos ya ocupados serán rechazados (no se sobrescriben).

---

## Codigos de Error Comunes

| Código HTTP | Significado |
|-------------|-------------|
| `200` | Petición exitosa (lectura) |
| `201` | Recurso(s) creado(s) exitosamente |
| `400` | Datos inválidos o incompletos |
| `401` | API Key no proporcionada o inválida |
| `404` | Viaje no encontrado |
| `429` | Límite de peticiones excedido (30/min) |
| `500` | Error interno del servidor |

**Formato de error estándar:**
```json
{
  "error": "Descripción del error.",
  "detalles": ["Detalle 1", "Detalle 2"]
}
```

---

## Flujo de Integracion Recomendado

```
┌──────────────┐                        ┌──────────────────┐
│ Su Sistema   │                        │ Aerorutas API    │
│ de Control   │                        │ (este servidor)  │
└──────┬───────┘                        └────────┬─────────┘
       │                                         │
       │  1. GET /viajes/                         │
       │────────────────────────────────────────>│
       │        Lista de viajes activos           │
       │<────────────────────────────────────────│
       │                                         │
       │  2. GET /viajes/{id}/asientos/           │
       │────────────────────────────────────────>│
       │     Mapa de asientos con disponibilidad  │
       │<────────────────────────────────────────│
       │                                         │
       │  3. Venden asiento(s) en su sistema      │
       │  ┌─────────────────────┐                │
       │  │ Proceso de venta    │                │
       │  │ interno de ustedes  │                │
       │  └─────────────────────┘                │
       │                                         │
       │  4. POST /viajes/{id}/ocupar-asientos/   │
       │────────────────────────────────────────>│
       │     Informan asientos vendidos           │
       │<────────────────────────────────────────│
       │     Reciben códigos de ticket            │
       │                                         │
       │  5. GET /viajes/{id}/pasajeros/ (opcional)│
       │────────────────────────────────────────>│
       │     Verificar lista actualizada          │
       │<────────────────────────────────────────│
```

---

## Ejemplos con cURL

### Listar viajes:
```bash
curl -X GET "http://localhost:8001/api/externo/viajes/" \
  -H "X-API-KEY: cU3g7kZWiFR4r1qYxjWEA89pL_awvhMIKFMFcZrpygA97_9yviyBijM0LEy-7JIZ"
```

### Ver asientos de un viaje:
```bash
curl -X GET "http://localhost:8001/api/externo/viajes/15/asientos/" \
  -H "X-API-KEY: cU3g7kZWiFR4r1qYxjWEA89pL_awvhMIKFMFcZrpygA97_9yviyBijM0LEy-7JIZ"
```

### Ocupar asientos:
```bash
curl -X POST "http://localhost:8001/api/externo/viajes/15/ocupar-asientos/" \
  -H "X-API-KEY: cU3g7kZWiFR4r1qYxjWEA89pL_awvhMIKFMFcZrpygA97_9yviyBijM0LEy-7JIZ" \
  -H "Content-Type: application/json" \
  -d '{
    "asientos": [
      { "numero": 10, "piso": 1, "nombre_pasajero": "Pedro López", "cedula_pasajero": "V-15678901" }
    ],
    "referencia_externa": "VENTA-001"
  }'
```

---

## Notas Importantes

1. **Sincronización en tiempo real:** Siempre consulte `/asientos/` antes de vender para evitar conflictos con reservas hechas en la web.

2. **Asientos pendientes (15 min):** Un asiento en estado `pendiente` está reservado temporalmente. Si el usuario no paga en 15 minutos, se libera automáticamente. Pueden considerar `pendiente` como "potencialmente disponible pronto".

3. **El campo `codigo_ticket`** generado al confirmar un asiento es el código que el pasajero presenta al abordar. Es único e irrepetible.

4. **Rate limiting:** Máximo 30 peticiones por minuto. Si necesitan más, contacten al administrador.

5. **El campo `referencia_externa`** no se almacena en nuestra base de datos, solo se retorna en la respuesta como confirmación. Úsenlo para trazabilidad interna.

---

**Contacto técnico:** administrador del sistema  
**API Key:** Proporcionada de forma segura por el administrador
