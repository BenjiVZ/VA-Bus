"""
Script para cargar datos REALES de Aerorutas de Venezuela.
Fuente: MARKETING AERORUTAS.docx + WhatsApp Image (tabla de flota)
Ejecutar: python seed_real_data.py
"""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from viajes.models import Ruta, Autobus, PisoAutobus, Viaje, ConfiguracionGeneral
from viajes.services import actualizar_tasa_bcv

# ═══════════════════════════════════════════════════════════
# 1. LIMPIAR DATOS EXISTENTES
# ═══════════════════════════════════════════════════════════
print("🗑️  Limpiando datos existentes...")
from reservas.models import Reserva
Reserva.objects.all().delete()
Viaje.objects.all().delete()
PisoAutobus.objects.all().delete()
Autobus.objects.all().delete()
Ruta.objects.all().delete()
print("   ✅ Datos anteriores eliminados")

# ═══════════════════════════════════════════════════════════
# 2. CONFIGURACIÓN GENERAL DE LA EMPRESA
# ═══════════════════════════════════════════════════════════
print("🏢 Configurando datos de la empresa...")
config = ConfiguracionGeneral.load()
config.nombre_empresa = 'AERORUTAS DE VENEZUELA, C.A.'
config.rif = 'J-50079785-0'
config.domicilio_fiscal = 'CTRA PANAMERICANA LOCAL NRO S/N SECTOR SABANA GRANDE, SABANA GRANDE, TRUJILLO, ZONA POSTAL 3110'
config.banco = 'BANCO DE VENEZUELA'
config.cuenta_bancaria = '01020589180000126201'
config.tipo_cuenta = 'CUENTA CORRIENTE'
config.telefono_contacto = '0412-671.87.62'
config.whatsapp_vendedor = '584126718762'
config.lema = 'RECORRIENDO CAMINOS POR TODA VENEZUELA'
config.mensaje_whatsapp = 'Hola, quiero confirmar mi reserva de autobús:\n\n{detalles}'
config.save()
print("   ✅ Configuración general actualizada")

# Actualizar tasa BCV
exito, msg = actualizar_tasa_bcv()
print(f"   {'✅' if exito else '⚠️'} Tasa BCV: {msg}")

# ═══════════════════════════════════════════════════════════
# 3. RUTAS REALES (del DOCX)
# ═══════════════════════════════════════════════════════════
print("🛣️  Creando rutas reales...")
rutas_data = [
    # (origen, destino, duracion_estimada)
    # RUTA 001: Mérida / El Vigía / Maracaibo y viceversa
    ('Mérida', 'Maracaibo', 'IDA: 08:30 PM - REGRESO: 08:30 PM'),
    # RUTA 002: Maracay/Valencia/El Vigía/Mérida y viceversa
    ('Maracay', 'Mérida', 'IDA: 05:30 PM - REGRESO: 06:15 PM'),
    # RUTA 003: Mérida, El Vigía, Tucaní, Caja Seca, Valencia, Maracay, Los Teques, Terminal La Bandera
    ('Mérida', 'Caracas (La Bandera)', 'IDA: 06:00 PM - REGRESO: 04:00 PM'),
    # RUTA 004: Maracay, Valencia, Barinas, Socopo, Santa Bárbara, San Cristóbal, San Antonio
    ('Maracay', 'San Antonio', 'IDA: 05:45 PM - REGRESO: 06:15 PM'),
    # RUTA 005: Maracay, Valencia, Maracaibo
    ('Maracay', 'Maracaibo', 'IDA: 06:00 PM - REGRESO: 06:30 PM'),
    # RUTA 006: Terminal La Bandera, Maracay, Valencia, Barinas, Socopo, Santa Bárbara, El Piñal, San Cristóbal
    ('Caracas (La Bandera)', 'San Cristóbal', 'IDA: 03:00-07:30 PM - REGRESO: 03:00-07:30 PM'),
    # RUTA 007: Terminal La Bandera, Maracay, Valencia, Barquisimeto, Maracaibo
    ('Caracas (La Bandera)', 'Maracaibo', 'IDA: 09:00 AM / 07:00 PM - REGRESO: 09:00 AM / 07:00 PM'),
    # RUTA 008: Maracaibo, Barquisimeto, Valencia, Maracay, Terminal La Bandera, Puerto La Cruz
    ('Maracaibo', 'Puerto La Cruz', 'IDA: 05:00 PM - REGRESO: 11:30 PM'),
    # RUTA 009: San Antonio, San Cristóbal, El Piñal, Santa Bárbara, Socopo, Barinas, Valencia, Maracay, Los Teques, La Bandera, Puerto La Cruz
    ('San Antonio', 'Puerto La Cruz', 'IDA: 11:00 AM - REGRESO: 11:00 AM'),
    # RUTA 010: Terminal La Bandera, Maracay, Valencia, Trujillo, Valera
    ('Caracas (La Bandera)', 'Valera', 'IDA: 05:00 PM - REGRESO: 05:00 PM'),
]
for origen, destino, dur in rutas_data:
    Ruta.objects.get_or_create(origen=origen, destino=destino, defaults={'duracion_estimada': dur})
print(f"   ✅ {Ruta.objects.count()} rutas creadas")

# ═══════════════════════════════════════════════════════════
# 4. FLOTA DE 29 AUTOBUSES (de la imagen WhatsApp)
# ═══════════════════════════════════════════════════════════
print("🚌 Creando flota de autobuses...")

# Datos extraídos de la imagen: (marca, color, año, capacidad, propietario)
flota = [
    ('VOLVO',          'AZUL Y BLANCO',       2007, 60, 'VEH.ARREN A AERORUTAS'),
    ('VOLVO',          'AZUL Y BLANCO',       2005, 60, 'VEH.ARREN A AERORUTAS'),
    ('VOLVO',          'BLANCO Y VERDE',      2004, 56, 'VEH.ARREN A AERORUTAS'),
    ('VOLVO',          'BLANCO',              2007, 60, 'AERORUTAS DE VZ'),
    ('VOLVO',          'BLANCO',              2007, 60, 'VEH.ARREN A AERORUTAS'),
    ('MERCEDES BENZ',  'BLANCO',              2007, 62, 'VEH.ARREN A AERORUTAS'),
    ('VOLVO',          'BLANCO Y MULTICOLOR', 2007, 60, 'AERORUTAS DE VZ'),
    ('SCANIA',         'BLANCO Y MULTICOLOR', 2005, 60, 'VEH.ARREN A AERORUTAS'),
    ('VOLVO',          'BLANCO Y VERDE',      2007, 60, 'VEH.ARREN A AERORUTAS'),
    ('VOLVO',          'BLANCO Y MULTICOLOR', 2008, 60, 'VEH.ARREN A AERORUTAS'),
    ('VOLVO',          'BLANCO',              2009, 46, 'VEH.ARREN A AERORUTAS'),
    ('VOLVO',          'AZUL Y BLANCO',       2006, 60, 'VEH.ARREN A AERORUTAS'),
    ('VOLVO',          'AZUL Y BLANCO',       2006, 60, 'VEH.ARREN A AERORUTAS'),
    ('MERCEDES BENZ',  'MULTICOLOR',          2007, 63, 'VEH.ARREN A AERORUTAS'),
    ('FAB. EXTRANJ',   'BLANCO MULTICOLOR',   2002, 49, 'VEH.ARREN A AERORUTAS'),
    ('FAB. EXTRANJ',   'BLANCO MULTICOLOR',   1997, 44, 'VEH.ARREN A AERORUTAS'),
    ('VOLVO',          'AZUL Y BLANCO',       2007, 60, 'VEH.ARREN A AERORUTAS'),
    ('VOLVO',          'BLANCO Y AZUL',       2007, 60, 'VEH.ARREN A AERORUTAS'),
    ('VOLVO',          'BLANCO',              2005, 60, 'VEH.ARREN A AERORUTAS'),
    ('VOLVO',          'BLANCO',              2007, 60, 'VEH.ARREN A AERORUTAS'),
    ('FAB. EXTRANJ',   'BLANCO MULTICOLOR',   2001, 48, 'VEH.ARREN A AERORUTAS'),
    ('VOLVO',          'AZUL Y BLANCO',       2005, 60, 'VEH.ARREN A AERORUTAS'),
    ('VOLVO',          'BLANCO',              2005, 42, 'VEH.ARREN A AERORUTAS'),
    ('VOLVO',          'BLANCO',              2005, 60, 'VEH.ARREN A AERORUTAS'),
    ('VOLVO',          'AZUL Y BLANCO',       2007, 60, 'VEH.ARREN A AERORUTAS'),
    ('VOLVO',          'BLANCO',              2006, 60, 'VEH.ARREN A AERORUTAS'),
    ('VOLVO',          'BLANCO Y VERDE',      2005, 60, 'VEH.ARREN A AERORUTAS'),
    ('VOLVO',          'BLANCO',              2007, 46, 'VEH.ARREN A AERORUTAS'),
    # Bus 29 (falta en la imagen visible, se completa con datos del DOCX - 29 unidades total)
]

# Determinamos si es de 1 piso o 2 pisos según capacidad:
# - Capacidad 42-49: 1 piso
# - Capacidad 56-63: 2 pisos
for i, (marca, color, anio, cap, prop) in enumerate(flota, start=1):
    placa = f'ADV-{i:03d}'  # Placa provisional
    
    # Determinar pisos
    if cap <= 49:
        num_pisos = 1
    else:
        num_pisos = 2
    
    nombre = f'{marca} {color} {anio} (#{i:02d})'
    
    bus, _ = Autobus.objects.get_or_create(
        placa=placa,
        defaults={
            'nombre': nombre,
            'marca': marca,
            'color': color,
            'anio': anio,
            'propietario': prop,
            'pisos': num_pisos,
        }
    )
    
    # Crear configuración de pisos vacía (los layouts se configurarán desde el admin)
    if num_pisos == 1:
        PisoAutobus.objects.get_or_create(
            autobus=bus, numero_piso=1,
            defaults={'filas': 10, 'columnas': 5, 'layout': []}
        )
    else:
        # Piso 1: generalmente menos asientos (baño al frente)
        PisoAutobus.objects.get_or_create(
            autobus=bus, numero_piso=1,
            defaults={'filas': 6, 'columnas': 5, 'layout': []}
        )
        # Piso 2: más asientos
        PisoAutobus.objects.get_or_create(
            autobus=bus, numero_piso=2,
            defaults={'filas': 10, 'columnas': 5, 'layout': []}
        )

print(f"   ✅ {Autobus.objects.count()} autobuses creados")
print(f"   ✅ {PisoAutobus.objects.count()} pisos configurados")

# ═══════════════════════════════════════════════════════════
# 5. RESUMEN
# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 50)
print("📊 RESUMEN DE DATOS CARGADOS")
print("=" * 50)
print(f"   Empresa: {config.nombre_empresa}")
print(f"   RIF: {config.rif}")
print(f"   Banco: {config.banco} - {config.tipo_cuenta}")
print(f"   Cuenta: {config.cuenta_bancaria}")
print(f"   Teléfono: {config.telefono_contacto}")
print(f"   Lema: {config.lema}")
print(f"   Autobuses: {Autobus.objects.count()}")
print(f"   Rutas: {Ruta.objects.count()}")
print(f"   Viajes: {Viaje.objects.count()}")
print("=" * 50)
print("🎉 ¡Datos reales cargados exitosamente!")
print("\n⚠️  NOTA: Las placas son provisionales (ADV-001 a ADV-028).")
print("   Actualízalas desde el admin de Django.")
print("⚠️  NOTA: Los layouts de asientos están vacíos.")
print("   Configúralos desde el editor visual en el admin.")
