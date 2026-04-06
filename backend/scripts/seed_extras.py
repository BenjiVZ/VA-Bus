"""Agrega autobuses de prueba: 2 pisos y puerta trasera."""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from viajes.models import Ruta, Autobus, PisoAutobus, Viaje
from datetime import date, time, timedelta

today = date.today()

# ── Bus 4: Doble Piso VIP (2 pisos, sin puerta trasera) ──
bus4, _ = Autobus.objects.get_or_create(
    placa='JKL-001',
    defaults={'nombre': 'Doble Piso VIP', 'pisos': 2}
)
PisoAutobus.objects.get_or_create(
    autobus=bus4, numero_piso=1,
    defaults={
        'filas': 6,
        'asientos_izquierda': 1,  # asientos tipo ejecutivo 1-2
        'asientos_derecha': 2,
        'asientos_fondo': 0,
        'tiene_puerta_trasera': False,
    }
)
PisoAutobus.objects.get_or_create(
    autobus=bus4, numero_piso=2,
    defaults={
        'filas': 10,
        'asientos_izquierda': 2,
        'asientos_derecha': 2,
        'asientos_fondo': 5,
        'tiene_puerta_trasera': False,
    }
)
print(f"Bus 4: {bus4.nombre} — Capacidad: {bus4.capacidad_total}")

# ── Bus 5: Urbano con puerta trasera ──
bus5, _ = Autobus.objects.get_or_create(
    placa='MNO-002',
    defaults={'nombre': 'Ruta Urbana Plus', 'pisos': 1}
)
PisoAutobus.objects.get_or_create(
    autobus=bus5, numero_piso=1,
    defaults={
        'filas': 8,
        'asientos_izquierda': 2,
        'asientos_derecha': 2,
        'asientos_fondo': 5,           # definidos pero no se generan
        'tiene_puerta_trasera': True,   # <-- puerta trasera activa
    }
)
print(f"Bus 5: {bus5.nombre} — Capacidad: {bus5.capacidad_total} (puerta trasera)")

# ── Bus 6: Doble piso con puerta trasera en piso 1 ──
bus6, _ = Autobus.objects.get_or_create(
    placa='PQR-003',
    defaults={'nombre': 'Gran Turismo', 'pisos': 2}
)
PisoAutobus.objects.get_or_create(
    autobus=bus6, numero_piso=1,
    defaults={
        'filas': 6,
        'asientos_izquierda': 2,
        'asientos_derecha': 2,
        'asientos_fondo': 5,
        'tiene_puerta_trasera': True,   # piso 1 tiene puerta trasera
    }
)
PisoAutobus.objects.get_or_create(
    autobus=bus6, numero_piso=2,
    defaults={
        'filas': 8,
        'asientos_izquierda': 2,
        'asientos_derecha': 2,
        'asientos_fondo': 5,
        'tiene_puerta_trasera': False,  # piso 2 normal
    }
)
print(f"Bus 6: {bus6.nombre} — Capacidad: {bus6.capacidad_total} (piso 1 puerta trasera)")

# ── Crear viajes de prueba con estos buses ──
rutas = list(Ruta.objects.all()[:3])
new_buses = [
    (bus4, 35.00, time(7, 0)),
    (bus5, 10.00, time(8, 30)),
    (bus6, 50.00, time(21, 0)),
]

c = 0
for bus, precio, hora in new_buses:
    for i, ruta in enumerate(rutas):
        fecha = today + timedelta(days=i + 1)
        _, created = Viaje.objects.get_or_create(
            ruta=ruta, autobus=bus, fecha_salida=fecha, hora_salida=hora,
            defaults={'precio_usd': precio, 'activo': True}
        )
        if created:
            c += 1

print(f"Viajes creados: {c}")
print("DONE!")
