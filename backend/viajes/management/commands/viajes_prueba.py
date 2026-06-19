"""Crea (o elimina) VIAJES DE PRUEBA con precios muy bajos para probar el flujo
de pago real (R4 Conecta) sin cobrar montos importantes.

El monto que cobra R4 es  Σ(precio_usd) × tasa_bcv  (en bolívares). Como
`precio_usd` solo admite 2 decimales, cada centavo de dólar equivale a ~1 unidad
de la tasa (hoy ~5,97 Bs). Por eso el precio se calcula al vuelo desde un objetivo
en Bs, redondeando hacia abajo para no pasarse del tope.

Uso:
    python manage.py viajes_prueba                 # crea con 12,24,36,48 Bs
    python manage.py viajes_prueba --montos 10,30  # crea con esos objetivos
    python manage.py viajes_prueba --eliminar      # borra los viajes de prueba

También se pueden eliminar desde el admin de Django: basta borrar la ruta
"PRUEBA — Pago" (o sus viajes), lo que arrastra reservas asociadas en cascada.
"""
from datetime import timedelta, time
from decimal import Decimal, ROUND_DOWN

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from viajes.models import Ruta, Autobus, Viaje, ConfiguracionGeneral

# Marcador con el que se identifican los viajes de prueba (crear y borrar).
RUTA_PRUEBA = ('PRUEBA — Pago', 'PRUEBA — Pago')


class Command(BaseCommand):
    help = ('Crea viajes de PRUEBA con precio bajo (≤ tope en Bs) para probar el '
            'pago R4, o los elimina con --eliminar.')

    def add_arguments(self, parser):
        parser.add_argument('--eliminar', action='store_true',
                            help='Elimina los viajes de prueba (y su ruta) y termina.')
        parser.add_argument('--montos', default='12,24,36,48',
                            help='Objetivos en Bs separados por coma. Default: 12,24,36,48')
        parser.add_argument('--max-bs', type=float, default=50.0,
                            help='Tope en Bs por viaje. Default: 50')
        parser.add_argument('--bus', type=int, default=None,
                            help='ID del autobús a usar. Default: el primero con asientos.')
        parser.add_argument('--dias', type=int, default=30,
                            help='Días en el futuro para la fecha de salida. Default: 30')

    # ── eliminar ──────────────────────────────────────────────────────────
    def _eliminar(self):
        ruta = Ruta.objects.filter(origen=RUTA_PRUEBA[0], destino=RUTA_PRUEBA[1]).first()
        if not ruta:
            self.stdout.write('No hay ruta de prueba. Nada que eliminar.')
            return
        n = Viaje.objects.filter(ruta=ruta).count()
        ruta.delete()  # cascada: viajes y sus reservas
        self.stdout.write(self.style.SUCCESS(
            f'Eliminados {n} viaje(s) de prueba y la ruta "PRUEBA - Pago".'))

    # ── crear ─────────────────────────────────────────────────────────────
    def handle(self, *args, **opts):
        if opts['eliminar']:
            return self._eliminar()

        config = ConfiguracionGeneral.load()
        tasa = config.tasa_bcv
        if not tasa or tasa <= 0:
            raise CommandError('Tasa BCV no configurada (0). Configúrala antes de crear precios.')

        if opts['bus']:
            bus = Autobus.objects.filter(pk=opts['bus']).first()
            if not bus:
                raise CommandError(f'No existe el autobús con id {opts["bus"]}.')
        else:
            bus = next((b for b in Autobus.objects.all() if b.capacidad_total > 0), None)
            if not bus:
                raise CommandError('No hay ningún autobús con asientos configurados.')

        max_bs = Decimal(str(opts['max_bs']))
        try:
            objetivos = [Decimal(x.strip()) for x in opts['montos'].split(',') if x.strip()]
        except Exception:
            raise CommandError('--montos debe ser una lista de números separados por coma.')
        if not objetivos:
            raise CommandError('No se indicó ningún monto en --montos.')

        ruta, _ = Ruta.objects.get_or_create(
            origen=RUTA_PRUEBA[0], destino=RUTA_PRUEBA[1],
            defaults={'duracion_estimada': '0h'},
        )
        # Empezar limpio: borra los viajes de prueba anteriores (no la ruta).
        Viaje.objects.filter(ruta=ruta).delete()

        fecha = timezone.now().date() + timedelta(days=opts['dias'])
        cent = Decimal('0.01')
        hora = 6
        creados = []
        for obj in objetivos:
            objetivo = min(obj, max_bs)
            precio = (objetivo / tasa).quantize(cent, rounding=ROUND_DOWN)
            if precio <= 0:
                self.stdout.write(self.style.WARNING(
                    f'  {obj} Bs es menor a 1 centavo de dólar (tasa {tasa}); omitido.'))
                continue
            real_bs = (precio * tasa).quantize(cent)
            # Salvaguarda: nunca pasar del tope.
            if real_bs > max_bs:
                precio -= cent
                real_bs = (precio * tasa).quantize(cent)
            v = Viaje.objects.create(
                ruta=ruta, autobus=bus, tipo_viaje='ida',
                fecha_salida=fecha, hora_salida=time(hour=min(hora, 23)),
                precio_usd=precio, activo=True,
            )
            creados.append((v, precio, real_bs))
            hora += 2

        if not creados:
            raise CommandError('No se creó ningún viaje (¿tasa muy alta para esos montos?).')

        self.stdout.write(self.style.SUCCESS(
            f'\nCreados {len(creados)} viaje(s) de prueba (ruta "PRUEBA - Pago"), '
            f'bus #{bus.id} ({bus.nombre}), salida {fecha}:'))
        for v, precio, real_bs in creados:
            self.stdout.write(
                f'  - Viaje {v.id}: ${precio} USD  ~  {real_bs} Bs  '
                f'(tasa {tasa})  a las {v.hora_salida.strftime("%H:%M")}')
        self.stdout.write(
            '\nAparecen en la web como la ruta "PRUEBA - Pago". '
            'Para borrarlos: python manage.py viajes_prueba --eliminar '
            'o elimina esa ruta desde el admin.')
