import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from viajes.models import Ruta, Autobus, Viaje
from datetime import date, time, timedelta

buses = list(Autobus.objects.all())
rutas = list(Ruta.objects.all()[:4])
precios = [25.00, 45.00, 15.00]
horas = [time(6, 0), time(10, 0), time(14, 0), time(20, 0), time(22, 0)]
today = date.today()
c = 0
for i, ruta in enumerate(rutas):
    for j in range(3):
        fecha = today + timedelta(days=j + 1)
        bus = buses[i % len(buses)]
        precio = precios[i % len(precios)]
        hora = horas[(i + j) % len(horas)]
        _, created = Viaje.objects.get_or_create(ruta=ruta, autobus=bus, fecha_salida=fecha, hora_salida=hora, defaults={'precio_usd': precio, 'activo': True})
        if created:
            c += 1
print(f"Created {c} viajes")
