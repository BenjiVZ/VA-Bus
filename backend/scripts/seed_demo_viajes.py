"""
Crea viajes de demo para los próximos 28 días.
Usa las rutas y buses existentes (con pisos configurados).

Uso:
    cd backend
    python scripts/seed_demo_viajes.py

Cada ruta recibe:
  - Hoy + algunos días siguientes (no todos, varía)
  - 2-3 horas distintas por día (mañana / tarde / noche)
  - Diferentes buses asignados
  - Mayoría ida; algunos ida_vuelta

Idempotente: usa get_or_create. Re-ejecutar no duplica viajes.
"""
import os
import sys
import django
from datetime import date, time, timedelta
import random

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
django.setup()

from viajes.models import Ruta, Autobus, Viaje  # noqa: E402

# ── Configuración ──
DIAS_FUTURO = 28          # Cubrir las próximas 4 semanas
HORAS_SALIDA = [
    time(5, 30),
    time(7, 0),
    time(9, 30),
    time(11, 0),
    time(14, 0),
    time(16, 30),
    time(19, 0),
    time(21, 30),
    time(23, 0),
]

# Precios sugeridos por ruta (USD) — fallback aleatorio si no aparece
PRECIOS_POR_RUTA = {
    # (origen, destino): precio_usd
    ('Mérida', 'Maracaibo'): 18.00,
    ('Maracay', 'Mérida'): 22.00,
    ('Mérida', 'Caracas (La Bandera)'): 25.00,
    ('Maracay', 'San Antonio'): 28.00,
    ('Maracay', 'Maracaibo'): 22.00,
    ('Caracas (La Bandera)', 'San Cristóbal'): 30.00,
    ('Caracas (La Bandera)', 'Maracaibo'): 26.00,
    ('Maracaibo', 'Puerto La Cruz'): 32.00,
    ('San Antonio', 'Puerto La Cruz'): 38.00,
    ('Caracas (La Bandera)', 'Valera'): 20.00,
}

# Seed para resultados reproducibles
random.seed(42)


def precio_para(ruta):
    key = (ruta.origen, ruta.destino)
    return PRECIOS_POR_RUTA.get(key, random.choice([15.0, 18.0, 20.0, 22.0, 25.0, 28.0, 30.0]))


def main():
    rutas = list(Ruta.objects.all())
    buses = list(
        Autobus.objects.filter(disponible=True)
        .prefetch_related('pisos_config')
    )
    # Solo buses con al menos un piso con asientos
    buses_validos = [b for b in buses if b.capacidad_total > 0]

    if not rutas:
        print('[ERROR] No hay rutas. Corre primero seed_data.py')
        return
    if not buses_validos:
        print('[ERROR] No hay buses con asientos configurados.')
        return

    hoy = date.today()
    creados = 0
    saltados = 0

    for ruta in rutas:
        precio = precio_para(ruta)
        # Por ruta: ~3 días de los próximos 28 con viajes
        # Distribuidos cada 2-4 días para que no sea diario
        dias_offset = sorted(random.sample(range(0, DIAS_FUTURO), k=8))

        for dia_off in dias_offset:
            fecha = hoy + timedelta(days=dia_off)
            # 2-3 horarios por día por ruta
            horarios_dia = random.sample(HORAS_SALIDA, k=random.choice([2, 3]))
            for hora in horarios_dia:
                bus = random.choice(buses_validos)
                # 15% de los viajes son ida y vuelta
                es_ida_vuelta = random.random() < 0.15
                tipo = 'ida_vuelta' if es_ida_vuelta else 'ida'
                fecha_vuelta = fecha + timedelta(days=random.choice([1, 2, 3])) if es_ida_vuelta else None
                hora_vuelta = random.choice(HORAS_SALIDA) if es_ida_vuelta else None

                _, created = Viaje.objects.get_or_create(
                    ruta=ruta,
                    autobus=bus,
                    fecha_salida=fecha,
                    hora_salida=hora,
                    defaults={
                        'tipo_viaje': tipo,
                        'fecha_vuelta': fecha_vuelta,
                        'hora_vuelta': hora_vuelta,
                        'precio_usd': precio,
                        'activo': True,
                        # Ventana abierta: desde hoy hasta el día anterior al viaje
                        'fecha_inicio_venta': None,
                        'fecha_fin_venta': fecha - timedelta(days=1) if dia_off > 0 else fecha,
                    },
                )
                if created:
                    creados += 1
                else:
                    saltados += 1

    total_futuros = Viaje.objects.filter(activo=True, fecha_salida__gte=hoy).count()

    print('')
    print('=== Demo viajes generados ===')
    print(f'   Creados:   {creados}')
    print(f'   Existian:  {saltados}')
    print(f'   Total futuros activos: {total_futuros}')
    print(f'   Rango: {hoy} -> {hoy + timedelta(days=DIAS_FUTURO)}')
    print('')
    print('Para limpiar viajes pasados:')
    print('   python manage.py shell -c "from viajes.models import Viaje; '
          'from datetime import date; '
          'Viaje.objects.filter(fecha_salida__lt=date.today()).delete()"')


if __name__ == '__main__':
    main()
