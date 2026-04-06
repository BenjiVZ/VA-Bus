"""Seed buses with JSON layout data for the new visual editor system."""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from viajes.models import Ruta, Autobus, PisoAutobus, Viaje
from datetime import date, time, timedelta

today = date.today()

# ── Helper to build a standard bus layout ──
def build_standard_layout(filas, izq, der, fondo=0, puerta_trasera=False, door_right_rows=None):
    """Build a 2D layout grid.
    Columns: [izq seats...] [aisle] [der seats...]
    """
    cols = izq + 1 + der  # +1 for aisle
    layout = []
    seat_num = 1

    for fila in range(filas):
        row = []
        skip_right = door_right_rows and (fila + 1) in door_right_rows

        # Left seats
        for c in range(izq):
            row.append({'type': 'seat', 'number': seat_num})
            seat_num += 1

        # Aisle
        row.append({'type': 'aisle'})

        # Right seats (or door)
        if skip_right:
            for c in range(der):
                row.append({'type': 'door'})
        else:
            for c in range(der):
                row.append({'type': 'seat', 'number': seat_num})
                seat_num += 1

        layout.append(row)

    # Back row (fondo)
    if fondo > 0 and not puerta_trasera:
        back_row = []
        for c in range(cols):
            if c < fondo:
                back_row.append({'type': 'seat', 'number': seat_num})
                seat_num += 1
            else:
                back_row.append({'type': 'empty'})
        layout.append(back_row)
    elif puerta_trasera:
        back_row = []
        for c in range(cols):
            back_row.append({'type': 'door'})
        layout.append(back_row)

    return layout, cols


# ── Delete old PisoAutobus data (clean start) ──
PisoAutobus.objects.all().delete()
Autobus.objects.all().delete()
Viaje.objects.all().delete()
print("Limpiados datos anteriores")

# ═══════════════════════════════════════════
# BUS 1: Express Dorado — 1 piso, estándar 2-2 con fondo
# ═══════════════════════════════════════════
bus1, _ = Autobus.objects.get_or_create(placa='ABC-123', defaults={'nombre': 'Express Dorado', 'pisos': 1})
layout1, cols1 = build_standard_layout(filas=10, izq=2, der=2, fondo=5)
PisoAutobus.objects.create(autobus=bus1, numero_piso=1, filas=11, columnas=cols1, layout=layout1)
print(f"Bus 1: {bus1.nombre} — {bus1.capacidad_total} asientos")

# ═══════════════════════════════════════════
# BUS 2: Premium Plus — 2 pisos
# ═══════════════════════════════════════════
bus2, _ = Autobus.objects.get_or_create(placa='DEF-456', defaults={'nombre': 'Premium Plus', 'pisos': 2})
layout2a, cols2a = build_standard_layout(filas=6, izq=1, der=2, fondo=0)
PisoAutobus.objects.create(autobus=bus2, numero_piso=1, filas=6, columnas=cols2a, layout=layout2a)
layout2b, cols2b = build_standard_layout(filas=10, izq=2, der=2, fondo=5)
PisoAutobus.objects.create(autobus=bus2, numero_piso=2, filas=11, columnas=cols2b, layout=layout2b)
print(f"Bus 2: {bus2.nombre} — {bus2.capacidad_total} asientos (2 pisos)")

# ═══════════════════════════════════════════
# BUS 3: Económico — 1 piso, 2-3 sin fondo
# ═══════════════════════════════════════════
bus3, _ = Autobus.objects.get_or_create(placa='GHI-789', defaults={'nombre': 'Economico', 'pisos': 1})
layout3, cols3 = build_standard_layout(filas=12, izq=2, der=3, fondo=0)
PisoAutobus.objects.create(autobus=bus3, numero_piso=1, filas=12, columnas=cols3, layout=layout3)
print(f"Bus 3: {bus3.nombre} — {bus3.capacidad_total} asientos")

# ═══════════════════════════════════════════
# BUS 4: Ruta Urbana — 1 piso, puerta trasera + puerta lateral derecha
# ═══════════════════════════════════════════
bus4, _ = Autobus.objects.get_or_create(placa='JKL-004', defaults={'nombre': 'Ruta Urbana', 'pisos': 1})
layout4, cols4 = build_standard_layout(filas=8, izq=2, der=2, puerta_trasera=True, door_right_rows={6, 7, 8})
PisoAutobus.objects.create(autobus=bus4, numero_piso=1, filas=9, columnas=cols4, layout=layout4)
print(f"Bus 4: {bus4.nombre} — {bus4.capacidad_total} asientos (puerta trasera + lateral)")

# ═══════════════════════════════════════════
# BUS 5: Gran Turismo — 2 pisos, piso 1 con puerta trasera
# ═══════════════════════════════════════════
bus5, _ = Autobus.objects.get_or_create(placa='MNO-005', defaults={'nombre': 'Gran Turismo', 'pisos': 2})
layout5a, cols5a = build_standard_layout(filas=6, izq=2, der=2, puerta_trasera=True)
PisoAutobus.objects.create(autobus=bus5, numero_piso=1, filas=7, columnas=cols5a, layout=layout5a)
layout5b, cols5b = build_standard_layout(filas=8, izq=2, der=2, fondo=5)
PisoAutobus.objects.create(autobus=bus5, numero_piso=2, filas=9, columnas=cols5b, layout=layout5b)
print(f"Bus 5: {bus5.nombre} — {bus5.capacidad_total} asientos (2 pisos, piso 1 puerta trasera)")

# ═══════════════════════════════════════════
# Crear viajes de prueba
# ═══════════════════════════════════════════
rutas = list(Ruta.objects.all()[:4])
buses = [bus1, bus2, bus3, bus4, bus5]
precios = [25.00, 45.00, 15.00, 10.00, 50.00]
horas = [time(6, 0), time(10, 0), time(14, 0), time(20, 0), time(22, 0)]

c = 0
for i, ruta in enumerate(rutas):
    for j in range(3):
        fecha = today + timedelta(days=j + 1)
        bus = buses[i % len(buses)]
        precio = precios[i % len(precios)]
        hora = horas[(i + j) % len(horas)]
        _, created = Viaje.objects.get_or_create(
            ruta=ruta, autobus=bus, fecha_salida=fecha, hora_salida=hora,
            defaults={'precio_usd': precio, 'activo': True}
        )
        if created:
            c += 1

print(f"\nViajes creados: {c}, Total: {Viaje.objects.count()}")
print("DONE!")
