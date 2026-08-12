"""Vigilante de cobros: confirma solo los pagos que el banco dejó en espera.

R4 responde AC00 ("en proceso") cuando el débito no se resuelve al instante, y
ese estado **solo avanza si alguien le vuelve a preguntar al banco**. Antes eso
dependía de un cron externo (`r4_validar_pendientes`); si no estaba puesto, el
dinero salía debitado y la reserva se quedaba EN VALIDACIÓN para siempre.

Este hilo lo hace desde el propio backend: arranca con el proceso, no hay nada
que instalar ni que correr a mano. El cliente puede cerrar la app y su boleto
se confirma igual (con su correo y todo).

Supone **un solo proceso** sirviendo (así corre `vabus-backend`: un daphne). Si
algún día se levantan varios workers, dos vigilantes podrían consultar la misma
operación a la vez y mandar el correo dos veces; en ese caso, apagarlo con
`R4_VIGILANTE=0` y volver al cron.
"""
import logging
import os
import sys
import threading
import time

from django.conf import settings

logger = logging.getLogger('r4conecta')

# Procesos que de verdad sirven peticiones. En producción es `daphne` (ver
# deploy/vabus-backend.service); en desarrollo, `manage.py runserver`.
#
# OJO: si algún día se cambia de servidor hay que agregarlo aquí o el vigilante
# no arranca. Se nota en el log: al arrancar escribe "Vigilante de cobros
# iniciado" (journalctl -u vabus-backend | grep Vigilante).
SERVIDORES = ('daphne', 'gunicorn', 'uvicorn', 'hypercorn')

# Cada cuánto revisa. La consulta de "¿hay algo en espera?" es un EXISTS sobre
# índice: cuando no hay nada pendiente el costo es despreciable.
INTERVALO = 60

# Máximo de operaciones por pasada, para no encadenar decenas de llamadas al
# banco en un mismo ciclo.
POR_PASADA = 25

# Una operación recién nacida se consulta en cada pasada (los AC00 de verdad se
# resuelven en minutos). Las que llevan más tiempo esperando se revisan de vez
# en cuando, para no martillar al banco con cobros que quedaron trabados.
FRESCA_MINUTOS = 30
PASADAS_ENTRE_REVISIONES_VIEJAS = 15

_iniciado = False
_candado = threading.Lock()


def iniciar():
    """Arranca el vigilante una sola vez, y solo cuando esto es un servidor."""
    global _iniciado

    if not getattr(settings, 'R4_VIGILANTE', True):
        return False
    if not _es_proceso_servidor():
        return False
    with _candado:
        if _iniciado:
            return False
        _iniciado = True
    threading.Thread(target=_bucle, name='r4-vigilante', daemon=True).start()
    logger.info('Vigilante de cobros iniciado (cada %ss)', INTERVALO)
    return True


def _es_proceso_servidor(argv=None, entorno=None):
    """Solo en el proceso que sirve peticiones.

    Nada de arrancarlo en migrate, collectstatic, tests o scripts sueltos: ahí
    haría llamadas al banco que nadie pidió.
    """
    argv = sys.argv if argv is None else argv
    entorno = os.environ if entorno is None else entorno
    ejecutable = os.path.basename(argv[0] if argv else '').lower()

    if any(s in ejecutable for s in SERVIDORES):
        return True

    if ejecutable.startswith('manage.py') or ejecutable.startswith('django-admin'):
        if len(argv) < 2 or argv[1] != 'runserver':
            return False
        # `runserver` sin --noreload levanta DOS procesos (el recargador y el
        # real). Solo el real trae RUN_MAIN, así que el vigilante no se duplica.
        return entorno.get('RUN_MAIN') == 'true'

    return False


def _bucle():
    pasada = 0
    while True:
        time.sleep(INTERVALO)   # dormir primero: el arranque ya tiene bastante
        pasada += 1
        try:
            _una_pasada(revisar_viejas=(pasada % PASADAS_ENTRE_REVISIONES_VIEJAS == 0))
        except Exception:  # noqa: BLE001 — el hilo NUNCA se puede morir
            logger.exception('Vigilante de cobros: fallo en la pasada %s', pasada)


def _una_pasada(revisar_viejas):
    from datetime import timedelta

    from django.db import connection
    from django.utils import timezone

    from . import services
    from .models import OperacionDebitoOTP
    from .operaciones import aplicar_respuesta

    try:
        qs = (OperacionDebitoOTP.objects
              .filter(estado='en_espera')
              .exclude(operacion_id=''))
        if not revisar_viejas:
            qs = qs.filter(updated_at__gte=timezone.now() - timedelta(minutes=FRESCA_MINUTOS))

        pendientes = list(qs.order_by('updated_at')[:POR_PASADA])
        if not pendientes:
            return

        # Si el tope recorta trabajo, que quede dicho: un "no hay nada" falso
        # sería peor que la demora.
        total = qs.count()
        if total > POR_PASADA:
            logger.warning('Vigilante: %s cobros en espera, se revisan %s en esta pasada',
                           total, POR_PASADA)

        for op in pendientes:
            try:
                estado = aplicar_respuesta(
                    op, services.consultar_operacion(op.operacion_id),
                    campo='consulta_response')
                if estado != 'en_espera':
                    logger.info('Vigilante: operacion %s resuelta -> %s', op.pk, estado)
            except services.R4Error as e:
                logger.info('Vigilante: banco no respondio por %s (%s)', op.pk, e.message)
            except Exception:  # noqa: BLE001 — una mala no puede frenar a las demás
                logger.exception('Vigilante: fallo al resolver la operacion %s', op.pk)
    finally:
        # El hilo tiene su propia conexión; soltarla para no ocupar cupo del
        # pool de la base administrada.
        connection.close()
