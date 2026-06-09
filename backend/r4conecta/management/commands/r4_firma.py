"""
Prueba la generación de la firma HMAC de R4 Conecta sin llamar al banco.

Ejemplos:
  python manage.py r4_firma --metodo generar_otp --banco 0192 --monto 50.00 \
      --telefono 04145555555 --cedula V12345678
  python manage.py r4_firma --metodo debito_inmediato --banco 0191 --monto 50.00 \
      --telefono 04145555555 --cedula V12345678 --otp 19807849
  python manage.py r4_firma --metodo consultar --id e63a7892-f00f-46a4-b7d1-a6e8ac7ab094
"""
from django.core.management.base import BaseCommand, CommandError
from r4conecta import services


class Command(BaseCommand):
    help = 'Genera y muestra la firma HMAC-SHA256 de R4 Conecta (sin llamar al banco).'

    def add_arguments(self, parser):
        parser.add_argument('--metodo', required=True,
                            choices=['generar_otp', 'debito_inmediato', 'consultar'])
        parser.add_argument('--banco', default='')
        parser.add_argument('--monto', default='')
        parser.add_argument('--telefono', default='')
        parser.add_argument('--cedula', default='')
        parser.add_argument('--otp', default='')
        parser.add_argument('--id', default='', dest='operacion_id')

    def handle(self, *args, **o):
        metodo = o['metodo']

        if metodo == 'generar_otp':
            monto = services._fmt_monto(o['monto'] or '0')
            mensaje = f"{o['banco']}{monto}{o['telefono']}{o['cedula']}"
        elif metodo == 'debito_inmediato':
            monto = services._fmt_monto(o['monto'] or '0')
            mensaje = f"{o['banco']}{o['cedula']}{o['telefono']}{monto}{o['otp']}"
        else:  # consultar
            if not o['operacion_id']:
                raise CommandError('Para --metodo consultar debes pasar --id.')
            mensaje = o['operacion_id']

        try:
            firma = services.firmar(mensaje)
        except services.R4Error as e:
            raise CommandError(str(e))

        self.stdout.write(f'Método:   {metodo}')
        self.stdout.write(f'Mensaje:  {mensaje!r}')
        self.stdout.write(self.style.SUCCESS(f'Firma:    {firma}'))
        self.stdout.write(f'Longitud: {len(firma)} (esperado 64 hex)')
