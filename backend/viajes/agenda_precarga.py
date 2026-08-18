"""Cronograma de los barridos del catálogo de Aerorutas, y disparo manual.

Esto NO programa nada: describe lo que el cron del servidor ya hace, para que
el operador vea a qué hora se refresca el catálogo y pueda adelantar un
barrido cuando haga falta. Si cambias las horas de aquí, hay que cambiar
también el crontab (`deploy/README-DEPLOY.md`) — y al revés.

Como esta pantalla podría estar mintiendo si el crontab quedó distinto, al
lado del cronograma se muestra la hora REAL de la última precarga
(`RutaAerorutasSnapshot.actualizado`), que sí es dato duro.

El botón manual se bloquea alrededor de cada barrido automático: dos barridos
a la vez se pisan escribiendo el mismo snapshot, y el que llegue segundo puede
disparar la protección del 60 % y dejar el catálogo viejo.
"""
import threading
from datetime import datetime, time, timedelta

from django.core.management import call_command
from django.utils import timezone

# Horas (de Venezuela) a las que corre cada barrido. El minuto es común.
MINUTO = 30
HORAS_COMPLETO = (1, 7, 13, 19)                          # cada 6 h — 15 días
HORAS_RAPIDO = (6, 8, 10, 12, 14, 16, 18, 20, 22)        # cada 2 h — solo hoy

# Ventana muerta del botón manual alrededor de cada barrido automático.
MIN_ANTES = 20
MIN_DESPUES = 10

MODOS = {
    'hoy': {
        'etiqueta': 'Rápido — solo hoy',
        'detalle': 'Refresca precios y cupos del día reusando los corredores '
                   'ya conocidos. No descubre corredores nuevos.',
        'dura': 'menos de un minuto',
        'args': {'dias': 1, 'usar_conocidos': True, 'intentos': 2, 'espera_red': 30},
    },
    'completo': {
        'etiqueta': 'Completo — 15 días',
        'detalle': 'Barre los pares de oficinas uno por uno: es el que encuentra '
                   'un corredor nuevo y el que rellena los días siguientes.',
        'dura': 'unos 5 minutos',
        'args': {'dias': 15, 'intentos': 3, 'espera_red': 30},
    },
}

# Un solo proceso daphne, así que un dict de módulo alcanza como candado.
# Ojo: esto NO ve los barridos del cron (son otro proceso); de eso se encarga
# la ventana muerta de arriba.
_corriendo = {'modo': None, 'desde': None}
_candado = threading.Lock()


def _puntos(dia):
    """[(datetime, modo)] de un día, ordenados."""
    tz = timezone.get_current_timezone()
    crudos = ([(h, 'completo') for h in HORAS_COMPLETO] +
              [(h, 'hoy') for h in HORAS_RAPIDO])
    return sorted(
        (timezone.make_aware(datetime.combine(dia, time(h, MINUTO)), tz), modo)
        for h, modo in crudos
    )


def proximo(ahora=None):
    """(cuándo, modo) del siguiente barrido automático. Puede caer mañana."""
    ahora = ahora or timezone.localtime()
    dia = timezone.localdate(ahora)
    for d in (dia, dia + timedelta(days=1)):
        for cuando, modo in _puntos(d):
            if cuando > ahora:
                return cuando, modo
    return None, None


def agenda(ahora=None):
    """Los barridos de HOY, marcando cuál ya pasó y cuál es el siguiente."""
    ahora = ahora or timezone.localtime()
    sigue, _ = proximo(ahora)
    filas = []
    for cuando, modo in _puntos(timezone.localdate(ahora)):
        filas.append({
            'hora': cuando.strftime('%H:%M'),
            'modo': modo,
            'etiqueta': MODOS[modo]['etiqueta'],
            'detalle': MODOS[modo]['detalle'],
            'pasado': cuando <= ahora,
            'proximo': cuando == sigue,
        })
    return filas


def en_curso():
    """Modo del barrido manual que está corriendo ahora, o ''."""
    return _corriendo['modo'] or ''


def estado_manual(ahora=None):
    """¿Se puede disparar un barrido a mano? -> (permitido, motivo)."""
    ahora = ahora or timezone.localtime()

    corriendo = _corriendo['modo']
    if corriendo:
        return False, ('Ya hay un barrido en curso (%s). Espera a que termine.'
                       % MODOS[corriendo]['etiqueta'])

    # Ayer también: el barrido de las 19:30 con MIN_DESPUES puede solaparse con
    # la medianoche según cómo se configuren las horas.
    dia = timezone.localdate(ahora)
    for d in (dia - timedelta(days=1), dia, dia + timedelta(days=1)):
        for cuando, modo in _puntos(d):
            abre = cuando + timedelta(minutes=MIN_DESPUES)
            if cuando - timedelta(minutes=MIN_ANTES) <= ahora <= abre:
                return False, (
                    'El barrido automático de las %s (%s) está pegado a esta hora. '
                    'Para no pisarlo, el botón se habilita a las %s.'
                    % (cuando.strftime('%H:%M'), MODOS[modo]['etiqueta'],
                       abre.strftime('%H:%M')))
    return True, ''


def lanzar(modo):
    """Dispara el barrido en segundo plano. -> (arrancó, mensaje)."""
    if modo not in MODOS:
        return False, 'Ese tipo de barrido no existe.'

    permitido, motivo = estado_manual()
    if not permitido:
        return False, motivo

    with _candado:
        if _corriendo['modo']:
            return False, 'Ya hay un barrido en curso.'
        _corriendo['modo'] = modo
        _corriendo['desde'] = timezone.localtime()

    def _run():
        from django.db import connections
        try:
            connections.close_all()
            call_command('precargar_rutas', **MODOS[modo]['args'])
        except Exception:
            # Red caída o barrido parcial: precargar_rutas conserva el catálogo
            # anterior antes que guardar uno malo. El cron reintenta solo.
            pass
        finally:
            _corriendo['modo'] = None
            _corriendo['desde'] = None
            connections.close_all()

    threading.Thread(target=_run, daemon=True).start()
    return True, ('Barrido «%s» lanzado; tarda %s. Recarga la pantalla para ver '
                  'el resultado.' % (MODOS[modo]['etiqueta'], MODOS[modo]['dura']))


# El comando que corre cada barrido, tal cual va en el crontab.
_CMD = ('cd /opt/va-bus/backend && venv/bin/python manage.py precargar_rutas %s'
        ' >> /opt/va-bus/backend/precargar_rutas.log 2>&1')
_ARGS_CRON = {'hoy': '--dias 1 --usar-conocidos', 'completo': '--dias 15'}


def lineas_crontab():
    """Las líneas de crontab que corresponden a este cronograma.

    Se generan desde las mismas constantes que dibuja la pantalla: así, si
    alguien cambia las horas aquí, el texto para pegar en el servidor cambia
    solo y no quedan los dos diciendo cosas distintas.

    CRON_TZ hace que las horas sean de Venezuela aunque el servidor esté en
    UTC (el droplet lo está). Sin eso, «06:30» serían las 02:30 de la mañana.
    """
    return ['CRON_TZ=America/Caracas'] + [
        '%d %s * * * %s' % (MINUTO, ','.join(str(h) for h in horas), _CMD % _ARGS_CRON[modo])
        for modo, horas in (('hoy', HORAS_RAPIDO), ('completo', HORAS_COMPLETO))
    ]
