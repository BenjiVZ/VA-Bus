"""
Valida las operaciones de Débito Inmediato que quedaron en espera (AC00),
consultando al banco (ConsultarOperaciones). Cuando el banco responde ACCP,
registra la referencia y confirma la reserva (libera/asigna la silla pagada).

Uso:
  python manage.py r4_validar_pendientes          # una pasada
  python manage.py r4_validar_pendientes --loop   # cada 30s (Ctrl+C para salir)
  python manage.py r4_validar_pendientes --loop --intervalo 30
"""
import time

from django.core.management.base import BaseCommand

from r4conecta import services
from r4conecta.models import OperacionDebitoOTP
from r4conecta.operaciones import aplicar_respuesta


class Command(BaseCommand):
    help = 'Consulta y resuelve las operaciones de Débito Inmediato en espera (AC00).'

    def add_arguments(self, parser):
        parser.add_argument('--loop', action='store_true',
                            help='Ejecuta en bucle continuo.')
        parser.add_argument('--intervalo', type=int, default=30,
                            help='Segundos entre pasadas en modo --loop (def. 30).')

    def _pasada(self):
        pendientes = OperacionDebitoOTP.objects.filter(
            estado='en_espera').exclude(operacion_id='')
        resueltas = 0
        for op in pendientes:
            try:
                resp = services.consultar_operacion(op.operacion_id)
            except services.R4Error as e:
                self.stderr.write(f'  Op {op.pk}: error al consultar: {e}')
                continue
            estado = aplicar_respuesta(op, resp, campo='consulta_response')
            self.stdout.write(f'  Op {op.pk} -> {estado} (code {op.code})')
            if estado != 'en_espera':
                resueltas += 1
        return pendientes.count(), resueltas

    def handle(self, *args, **o):
        if not o['loop']:
            total, resueltas = self._pasada()
            self.stdout.write(self.style.SUCCESS(
                f'Pendientes procesadas: {total} | resueltas: {resueltas}'))
            return

        intervalo = o['intervalo']
        self.stdout.write(self.style.SUCCESS(
            f'Validando operaciones en espera cada {intervalo}s (Ctrl+C para salir)…'))
        try:
            while True:
                self._pasada()
                time.sleep(intervalo)
        except KeyboardInterrupt:
            self.stdout.write('\nDetenido.')
