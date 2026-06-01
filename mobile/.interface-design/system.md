# Aerorutas de Venezuela — Design System

## Intent

**Who:** Venezolano viajando entre ciudades. Está en su teléfono — quizá en la cola del terminal, quizá en casa planeando con días. Necesita confiar en que su asiento es suyo, ver el precio en bolívares al cambio del día, y mostrar algo claro al chofer cuando aborde. Paga con transferencia, pago móvil, divisas o Zelle.

**What:** Buscar viaje → escoger asiento → subir comprobante → recibir boleto con QR → abordar.

**Feel:** **Boleto digital con peso oficial.** Honesto, sólido, con autoridad de algo institucional. Ni "friendly tech startup", ni "corporate B2B". Entre la planilla del chofer y el ticket térmico del terminal.

## Direction

Cada elemento es parte de un sistema de boletería:
- **Tipografía con peso de impresión oficial** — Inter para UI, **Roboto Mono para datos** (códigos, horas, asientos, referencias)
- **Cream paper surface** como alternativa cálida al gris frío (tickets, comprobantes)
- **Sellos en lugar de badges** — status con rotación leve y peso de estampado
- **Perforaciones donde se separa información** — tickets y stubs
- **Navy + dorado como colores oficiales** (no decorativos, identitarios)
- **Densidad media-alta** — el venezolano que viaja quiere info clara, no whitespace SaaS

## Signature

**El boleto-objeto.** Cada ticket no es una card UI, es un boleto físico digitalizado: muescas perforadas, código en monospace tipo impresora térmica, sello "PAGO CONFIRMADO" con rotación. Esta firma reaparece en pequeño en otras pantallas (stub del ticket en Mis Reservas, mismo border treatment en QRs, mismo tratamiento del código).

## Colors (mapean a primitivos en lib/config/theme.dart)

### Foreground
- `text-primary` — `gray-900 #0E1525` — texto principal, valores
- `text-secondary` — `gray-700 #3D4455` — texto soporte
- `text-tertiary` — `gray-600 #5A6175` — metadata, labels
- `text-muted` — `gray-500 #7D8494` — disabled, placeholders

### Background (elevación)
- `bg-canvas` — `gray-50 #F7F8FB` — fondo de página
- `bg-surface` — `white` — cards, surfaces base
- `bg-paper` — `#FFFBF3` — **NUEVO** crema cálido para tickets, comprobantes y elementos "documento"
- `bg-elevated` — `white` con shadow `md` — dropdowns, dialogs

### Brand (oficiales)
- `brand-primary` — `blue-500 #1A3A6B` — navy del bus
- `brand-primary-hover` — `blue-600 #142E55`
- `brand-primary-dark` — `blue-700 #0E2240` — hero gradient end
- `brand-accent` — `yellow-400 #F5C842` — dorado del faro/sello

### Semantic (significan, no decoran)
- `success` — `green-500 #00875A` — confirmado, validado
- `warning` — `yellow-600 #D49A10` — pendiente, urgente
- `danger` — `red-500 #C62828` — cancelado, error, sello rechazado
- `info` — `blue-500 #1A3A6B` — en validación

### Borders
- `border-subtle` — `gray-100 #EBEDF1` rgba — separación quieta
- `border-standard` — `gray-200 #DDE0E6` — bordes normales
- `border-strong` — `gray-300 #C1C5CF` — emphasis
- `border-focus` — `blue-500 #1A3A6B 2px` — focus rings

## Typography

- **UI:** Inter — pesos 400/500/600/700/800, escala display/headline/title/body/label
- **Data:** Roboto Mono — códigos de ticket, horas (HH:MM), número de referencia, asientos en contextos oficiales
- **Hierarchy:** size + weight + tracking (no solo size)

## Depth strategy

**Borders + subtle shadow** combinados:
- Cards: `border: 1px borderSubtle` + `shadow-sm` opcional
- Search card / boarding pass: `shadow-lg` (peso de objeto físico)
- Botones primarios: `box-shadow` color navy (sutil — autoridad sin grito)
- No mezclar con shadows dramáticos

## Spacing

Base unit **4pt**. Escala: 4 · 8 · 12 · 16 · 20 · 24 · 32 · 48
- Micro (4-8): icon gaps, paddings internos de chips
- Component (12-16): padding interno de cards y inputs
- Section (20-32): separación entre grupos
- Major (48+): entre secciones principales

## Border radius

- **Sharp (4px):** sellos, stamps
- **Small (8px):** chips, badges, dates en quick-pick
- **Medium (12px):** inputs, buttons
- **Large (16-18px):** cards
- **XL (20-24px):** hero, modals, boarding pass

## Components

### Stamps (reemplazan badges genéricos)

Para estados oficiales con peso de estampado. Rotación leve (`-2°` a `2°`), border doble, fuente monospace, tracking amplio.

```dart
OfficialStamp(
  label: 'PAGADO',
  color: AppColors.green500,
)
```

Variantes:
- `PAGO CONFIRMADO` (verde)
- `EN VALIDACIÓN` (azul)
- `PENDIENTE` (amarillo)
- `RECHAZADO` (rojo, opcional rotación más fuerte)

### Boarding pass

Card con muescas semicirculares laterales + perforación punteada interna. Top con gradient navy, bottom con cream paper. Códigos en Roboto Mono con letterspacing amplio.

### Tablero de salidas (reemplaza stats pills)

En home, en lugar de "10 rutas / 28 buses / 6+ viajeros", mostrar las **próximas 3-4 salidas reales**:
```
┌────────────────────────────────────┐
│ PRÓXIMAS SALIDAS                   │
│ 14:30  Mérida → Maracaibo    $12  │  ← Roboto Mono en hora
│ 16:00  Caracas → Valencia    $8   │
│ 18:45  Maracay → Mérida      $15  │
└────────────────────────────────────┘
```

### Quick-pick date chips
"Hoy", "Mañana", calendar opener — coherente, todos mismo radius.

## Avoid (registro de defaults rechazados)

1. **Stats pills genéricas SaaS** (Rutas/Buses/Viajeros) → tablero de salidas real
2. **Material 3 chips ovalados para estados** → stamps oficiales
3. **Friendly-tech tipografía sin peso** → monospace en datos oficiales
4. **Whitespace SaaS** → densidad de información clara
5. **Sombras dramáticas decorativas** → border + sombra sutil
6. **Multiple accent colors** → solo navy y dorado son identitarios; semánticos son cuando significan

## Saved patterns

- `lib/widgets/official_stamp.dart` — sellos
- `lib/screens/reservas/ticket_screen.dart` — boarding pass (referencia de signature)
- `lib/config/theme.dart` — tokens
