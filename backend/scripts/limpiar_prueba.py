"""
Elimina la DATA DE PRUEBA (viajes/rutas/autobuses locales) del sistema.

CONSERVA:
  - Los viajes ESPEJO de Aerorutas (aerorutas_codrut != '') — son las ventas reales.
  - Cualquier viaje local con una reserva CONFIRMADA (venta real) y todos sus datos.

Solo borra los viajes locales de prueba (los que crean los seeds/reset_viajes),
sus reservas pendientes/canceladas (en cascada) y las rutas/autobuses que queden
huérfanos. Es seguro correrlo en producción.

Uso:
    cd /opt/va-bus/backend && venv/bin/python scripts/limpiar_prueba.py
"""
import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django  # noqa: E402
django.setup()

from django.db.models import Count  # noqa: E402
from viajes.models import Ruta, Autobus, Viaje  # noqa: E402
from reservas.models import Reserva  # noqa: E402

print('=' * 60)
print('LIMPIEZA DE DATA DE PRUEBA')
print('(conserva Aerorutas y ventas confirmadas)')
print('=' * 60)

# 1. Viajes locales de prueba = NO espejo de Aerorutas.
locales = Viaje.objects.filter(aerorutas_codrut='')

# Proteger los que tengan una venta CONFIRMADA (por si hubo compra real local).
protegidos = set(
    Reserva.objects.filter(estado='confirmado', viaje__in=locales)
    .values_list('viaje_id', flat=True)
)
a_borrar = locales.exclude(id__in=protegidos)

print(f'  Viajes locales encontrados:            {locales.count()}')
print(f'  Protegidos (con venta confirmada):     {len(protegidos)}')
print(f'  Viajes de prueba a eliminar:           {a_borrar.count()}')

total, detalle = a_borrar.delete()
print(f'  -> {total} objetos eliminados en cascada:')
for modelo, n in detalle.items():
    print(f'       {modelo}: {n}')

# 2. Rutas huérfanas (sin ningún viaje que las use).
rutas_orf = Ruta.objects.annotate(n=Count('viajes')).filter(n=0)
n_rutas = rutas_orf.count()
rutas_orf.delete()
print(f'  Rutas huérfanas eliminadas:            {n_rutas}')

# 3. Autobuses huérfanos (sin ningún viaje).
buses_orf = Autobus.objects.annotate(n=Count('viajes')).filter(n=0)
n_buses = buses_orf.count()
buses_orf.delete()
print(f'  Autobuses huérfanos eliminados:        {n_buses}')

print('-' * 60)
print('RESUMEN FINAL')
espejos = Viaje.objects.exclude(aerorutas_codrut='').count()
print(f'  Viajes restantes:    {Viaje.objects.count()} (espejos Aerorutas: {espejos})')
print(f'  Rutas restantes:     {Ruta.objects.count()}')
print(f'  Autobuses restantes: {Autobus.objects.count()}')
print('=' * 60)
print('Listo. Los desplegables de origen/destino salen de las oficinas de')
print('Aerorutas (no de estas rutas), así que ya no dependen de esta data.')
