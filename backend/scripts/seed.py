import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from viajes.models import Ruta, Autobus, PisoAutobus, Viaje, ConfiguracionGeneral
from viajes.services import actualizar_tasa_bcv
from datetime import date, time, timedelta

# Config
config = ConfiguracionGeneral.load()
config.whatsapp_vendedor = '584121234567'
config.nombre_empresa = 'Aerorutas de Venezuela'
config.mensaje_whatsapp = 'Hola, quiero confirmar mi reserva:\n\n{detalles}'
config.save()
print("Config OK")

exito, msg = actualizar_tasa_bcv()
print(f"Tasa BCV: {msg}")

# Rutas
rutas_data = [
    ('Caracas', 'Maracaibo', '12 horas'),
    ('Caracas', 'Valencia', '3 horas'),
    ('Caracas', 'Barquisimeto', '5 horas'),
    ('Valencia', 'Maracaibo', '9 horas'),
    ('Caracas', 'Merida', '14 horas'),
    ('Maracaibo', 'Barquisimeto', '6 horas'),
]
for o, d, dur in rutas_data:
    Ruta.objects.get_or_create(origen=o, destino=d, defaults={'duracion_estimada': dur})
print(f"Rutas: {Ruta.objects.count()}")

# Buses
bus1, _ = Autobus.objects.get_or_create(placa='ABC-123', defaults={'nombre': 'Express Dorado', 'pisos': 1})
PisoAutobus.objects.get_or_create(autobus=bus1, numero_piso=1, defaults={'filas': 10, 'asientos_izquierda': 2, 'asientos_derecha': 2, 'asientos_fondo': 5})

bus2, _ = Autobus.objects.get_or_create(placa='DEF-456', defaults={'nombre': 'Premium Plus', 'pisos': 2})
PisoAutobus.objects.get_or_create(autobus=bus2, numero_piso=1, defaults={'filas': 8, 'asientos_izquierda': 2, 'asientos_derecha': 2, 'asientos_fondo': 3})
PisoAutobus.objects.get_or_create(autobus=bus2, numero_piso=2, defaults={'filas': 10, 'asientos_izquierda': 2, 'asientos_derecha': 2, 'asientos_fondo': 5})

bus3, _ = Autobus.objects.get_or_create(placa='GHI-789', defaults={'nombre': 'Economico', 'pisos': 1})
PisoAutobus.objects.get_or_create(autobus=bus3, numero_piso=1, defaults={'filas': 12, 'asientos_izquierda': 2, 'asientos_derecha': 3, 'asientos_fondo': 0})
print(f"Autobuses: {Autobus.objects.count()}")

# Viajes
rutas = list(Ruta.objects.all()[:4])
buses = [bus1, bus2, bus3]
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
print(f"Viajes creados: {c}, Total: {Viaje.objects.count()}")
print("DONE!")
