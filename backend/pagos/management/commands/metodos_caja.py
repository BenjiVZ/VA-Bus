"""
Crea (o actualiza) los métodos de pago que usa la CAJA de taquilla.

Es idempotente: se puede correr las veces que haga falta. Solo marca
`disponible_caja`; no toca los métodos que ya usa la web.

Uso:
    python manage.py metodos_caja
    python manage.py metodos_caja --listar     # solo muestra cómo quedó
"""
from django.core.management.base import BaseCommand

from pagos.models import MetodoPago

# (nombre, tipo, moneda, descripción)
METODOS_CAJA = [
    ('Efectivo Bs.',      'efectivo',   'BS',  'Pago en bolívares en taquilla'),
    ('Efectivo $',        'divisas',    'USD', 'Pago en dólares en taquilla'),
    ('Débito',            'debito',     'BS',  'Punto de venta en taquilla'),
    ('Pago Móvil',        'pago_movil', 'BS',  'Transferencia inmediata'),
    ('Cashea',            'cashea',     'BS',  'Compra a cuotas con Cashea'),
]


class Command(BaseCommand):
    help = 'Crea/actualiza los métodos de pago de la caja de taquilla.'

    def add_arguments(self, parser):
        parser.add_argument('--listar', action='store_true',
                            help='Solo muestra los métodos habilitados para caja.')

    def _listar(self):
        qs = MetodoPago.objects.filter(disponible_caja=True).order_by('orden', 'nombre')
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'\nMétodos habilitados en CAJA: {qs.count()}'))
        for m in qs:
            estado = 'activo' if m.activo else 'INACTIVO'
            self.stdout.write(
                f'  {m.nombre[:24].ljust(24)} {m.get_tipo_display()[:26].ljust(26)} '
                f'{m.moneda}  [{estado}]')
        if not qs.exists():
            self.stdout.write(self.style.WARNING('  (ninguno)'))

    def handle(self, *args, **o):
        if o['listar']:
            return self._listar()

        creados, actualizados = 0, 0
        for orden, (nombre, tipo, moneda, desc) in enumerate(METODOS_CAJA, start=1):
            metodo, creado = MetodoPago.objects.get_or_create(
                nombre=nombre,
                defaults={
                    'tipo': tipo, 'moneda': moneda, 'descripcion': desc,
                    'activo': True, 'orden': orden,
                    'disponible_caja': True,
                    # Son métodos de mostrador: no se le ofrecen al cliente en la web.
                    'disponible_web': False,
                },
            )
            if creado:
                creados += 1
                self.stdout.write(self.style.SUCCESS(f'  + creado: {nombre}'))
            else:
                # Ya existía (quizá lo usa la web): solo lo habilitamos en caja.
                if not metodo.disponible_caja:
                    metodo.disponible_caja = True
                    metodo.save(update_fields=['disponible_caja'])
                    actualizados += 1
                    self.stdout.write(f'  ~ habilitado en caja: {nombre}')
                else:
                    self.stdout.write(f'  = ya estaba listo: {nombre}')

        self.stdout.write(self.style.SUCCESS(
            f'\nListo: {creados} creado(s), {actualizados} habilitado(s) en caja.'))
        self._listar()
