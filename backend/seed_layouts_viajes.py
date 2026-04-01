"""
Genera layouts de asientos (solo asientos) para los 28 buses
y crea viajes para las 10 rutas con fechas próximas.
Ejecutar: python seed_layouts_viajes.py
"""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from viajes.models import Ruta, Autobus, PisoAutobus, Viaje
from datetime import date, time, timedelta


def build_seat_layout(target_seats, pisos):
    """
    Genera un layout sencillo (solo asientos + pasillo) para un bus.
    Distribución estándar: 2 asientos | pasillo | 2 asientos = 4 por fila.
    """
    if pisos == 1:
        # Todo en 1 piso
        seats_per_row = 4  # 2-2
        filas = target_seats // seats_per_row
        remainder = target_seats % seats_per_row
        if remainder > 0:
            filas += 1  # fila extra parcial

        layout = []
        seat_num = 1
        for f in range(filas):
            row = []
            # 2 asientos izquierda
            for c in range(2):
                if seat_num <= target_seats:
                    row.append({'type': 'seat', 'number': seat_num})
                    seat_num += 1
                else:
                    row.append({'type': 'empty'})
            # pasillo
            row.append({'type': 'aisle'})
            # 2 asientos derecha
            for c in range(2):
                if seat_num <= target_seats:
                    row.append({'type': 'seat', 'number': seat_num})
                    seat_num += 1
                else:
                    row.append({'type': 'empty'})
            layout.append(row)

        return [(1, filas, 5, layout)]

    else:
        # 2 pisos - distribuir asientos
        # Piso 1: ~40% de asientos (menos espacio por baño/escaleras)
        # Piso 2: ~60% de asientos
        piso1_seats = int(target_seats * 0.35)
        # Redondear a múltiplo de 4
        piso1_seats = (piso1_seats // 4) * 4
        if piso1_seats < 8:
            piso1_seats = 8
        piso2_seats = target_seats - piso1_seats

        pisos_result = []
        for piso_num, num_seats in [(1, piso1_seats), (2, piso2_seats)]:
            seats_per_row = 4
            filas = num_seats // seats_per_row
            remainder = num_seats % seats_per_row
            if remainder > 0:
                filas += 1

            layout = []
            seat_num = 1
            for f in range(filas):
                row = []
                for c in range(2):
                    if seat_num <= num_seats:
                        row.append({'type': 'seat', 'number': seat_num})
                        seat_num += 1
                    else:
                        row.append({'type': 'empty'})
                row.append({'type': 'aisle'})
                for c in range(2):
                    if seat_num <= num_seats:
                        row.append({'type': 'seat', 'number': seat_num})
                        seat_num += 1
                    else:
                        row.append({'type': 'empty'})
                layout.append(row)

            pisos_result.append((piso_num, filas, 5, layout))

        return pisos_result


# ═══════════════════════════════════════════════════════════
# 1. GENERAR LAYOUTS PARA TODOS LOS BUSES
# ═══════════════════════════════════════════════════════════
print("🪑 Generando layouts de asientos...")

# Capacidades esperadas por bus (de la imagen)
capacidades = {
    'ADV-001': 60, 'ADV-002': 60, 'ADV-003': 56, 'ADV-004': 60,
    'ADV-005': 60, 'ADV-006': 62, 'ADV-007': 60, 'ADV-008': 60,
    'ADV-009': 60, 'ADV-010': 60, 'ADV-011': 46, 'ADV-012': 60,
    'ADV-013': 60, 'ADV-014': 63, 'ADV-015': 49, 'ADV-016': 44,
    'ADV-017': 60, 'ADV-018': 60, 'ADV-019': 60, 'ADV-020': 60,
    'ADV-021': 48, 'ADV-022': 60, 'ADV-023': 42, 'ADV-024': 60,
    'ADV-025': 60, 'ADV-026': 60, 'ADV-027': 60, 'ADV-028': 46,
}

# Limpiar pisos existentes y recrear
PisoAutobus.objects.all().delete()

for bus in Autobus.objects.all().order_by('placa'):
    target = capacidades.get(bus.placa, 60)
    pisos_data = build_seat_layout(target, bus.pisos)

    for piso_num, filas, cols, layout in pisos_data:
        PisoAutobus.objects.create(
            autobus=bus,
            numero_piso=piso_num,
            filas=filas,
            columnas=cols,
            layout=layout
        )

    # Verificar capacidad
    bus.refresh_from_db()
    cap = bus.capacidad_total
    print(f"   {bus.placa} | {bus.marca} {bus.anio} | {bus.pisos}P | Cap: {cap} (esperado: {target})")

print(f"\n   ✅ {PisoAutobus.objects.count()} pisos creados para {Autobus.objects.count()} buses")

# ═══════════════════════════════════════════════════════════
# 2. CREAR VIAJES PARA LAS PRÓXIMAS 2 SEMANAS
# ═══════════════════════════════════════════════════════════
print("\n🚌 Creando viajes...")

# Limpiar viajes existentes
Viaje.objects.all().delete()

today = date.today()

# Horarios extraídos de las rutas (del DOCX)
# Estructura: (ruta_origen, ruta_destino, hora_ida, precio_usd)
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

    # Asignar buses rotativamente (2-3 buses por ruta)
    for dia in range(14):  # 2 semanas
        fecha = today + timedelta(days=dia + 1)
        bus = buses[(ruta_idx + dia) % len(buses)]

        _, created = Viaje.objects.get_or_create(
            ruta=ruta,
            autobus=bus,
            fecha_salida=fecha,
            hora_salida=hora,
            defaults={
                'precio_usd': precio,
                'activo': True
            }
        )
        if created:
            viajes_creados += 1

print(f"\n   ✅ {viajes_creados} viajes creados para las próximas 2 semanas")
print(f"   Total viajes en DB: {Viaje.objects.count()}")

# ═══════════════════════════════════════════════════════════
# RESUMEN FINAL
# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 50)
print("📊 RESUMEN FINAL")
print("=" * 50)
print(f"   Autobuses: {Autobus.objects.count()}")
print(f"   Pisos configurados: {PisoAutobus.objects.count()}")
print(f"   Rutas: {Ruta.objects.count()}")
print(f"   Viajes: {Viaje.objects.count()}")
print("=" * 50)
print("🎉 ¡Layouts y viajes creados exitosamente!")
