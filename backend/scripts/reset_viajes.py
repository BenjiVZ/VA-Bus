"""
Limpia la DB y recrea viajes con 1 año de expiración.
Mantiene las rutas, autobuses y layouts.
Ejecutar: python reset_viajes.py
"""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from viajes.models import Ruta, Autobus, PisoAutobus, Viaje
from reservas.models import Reserva
from pagos.models import ComprobantePago
from datetime import date, time, timedelta

print("=" * 55)
print("🧹 LIMPIANDO BASE DE DATOS")
print("=" * 55)

# Limpiar en orden por dependencias
comprobantes = ComprobantePago.objects.count()
ComprobantePago.objects.all().delete()
print(f"   ❌ {comprobantes} comprobantes eliminados")

reservas = Reserva.objects.count()
Reserva.objects.all().delete()
print(f"   ❌ {reservas} reservas eliminadas")

viajes = Viaje.objects.count()
Viaje.objects.all().delete()
print(f"   ❌ {viajes} viajes eliminados")

print(f"\n   ✅ DB limpia. Rutas ({Ruta.objects.count()}) y Autobuses ({Autobus.objects.count()}) conservados.")

# ═══════════════════════════════════════════════════════════
# RECREAR VIAJES CON 1 AÑO DE EXPIRACIÓN
# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("🚌 CREANDO VIAJES (1 año de expiración)")
print("=" * 55)

today = date.today()
expiracion = today + timedelta(days=365)  # 1 año

# Rutas y precios del sistema
rutas_viajes = [
    ('Mérida', 'Maracaibo',               time(20, 30), 25.00),
    ('Maracay', 'Mérida',                  time(17, 30), 30.00),
    ('Mérida', 'Caracas (La Bandera)',     time(18, 0),  30.00),
    ('Maracay', 'San Antonio',             time(17, 45), 45.00),
    ('Maracay', 'Maracaibo',               time(18, 0),  32.00),
    ('Caracas (La Bandera)', 'San Cristóbal', time(15, 0), 35.00),
    ('Caracas (La Bandera)', 'Maracaibo',  time(9, 0),   28.00),
    ('Maracaibo', 'Puerto La Cruz',        time(17, 0),  55.00),
    ('San Antonio', 'Puerto La Cruz',      time(11, 0),  55.00),
    ('Caracas (La Bandera)', 'Valera',     time(17, 0),  25.00),
]

buses = list(Autobus.objects.all().order_by('placa'))
viajes_creados = 0

for ruta_idx, (origen, destino, hora, precio) in enumerate(rutas_viajes):
    try:
        ruta = Ruta.objects.get(origen=origen, destino=destino)
    except Ruta.DoesNotExist:
        print(f"   ⚠️ Ruta {origen} → {destino} no encontrada, saltando...")
        continue

    # Crear viajes diarios por 30 días, rotando buses
    for dia in range(30):
        fecha = today + timedelta(days=dia + 1)
        bus = buses[(ruta_idx + dia) % len(buses)]

        Viaje.objects.create(
            ruta=ruta,
            autobus=bus,
            tipo_viaje='ida',
            fecha_salida=fecha,
            hora_salida=hora,
            precio_usd=precio,
            activo=True,
            fecha_fin_venta=expiracion,  # 1 año de expiración
        )
        viajes_creados += 1

    print(f"   ✅ {origen} → {destino} | {hora.strftime('%H:%M')} | ${precio} | 30 viajes")

# ═══════════════════════════════════════════════════════════
# RESUMEN
# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 55)
print("📊 RESUMEN FINAL")
print("=" * 55)
print(f"   Rutas:     {Ruta.objects.count()}")
print(f"   Autobuses: {Autobus.objects.count()}")
print(f"   Pisos:     {PisoAutobus.objects.count()}")
print(f"   Viajes:    {Viaje.objects.count()}")
print(f"   Reservas:  {Reserva.objects.count()}")
print(f"   Expiración: {expiracion.strftime('%d/%m/%Y')}")
print("=" * 55)
print("🎉 ¡Listo! Viajes creados con 1 año de expiración.")
