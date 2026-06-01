"""
Helper para que vistas síncronas (DRF normales) puedan emitir eventos
al grupo de Channels del viaje correspondiente.

Uso:
    from viajes.ws_broadcast import broadcast_seat_change
    broadcast_seat_change(viaje_id=1, numero=12, piso=1,
                          estado='locked', usuario_id=request.user.id)

Si Channels no está disponible (ej. tests, scripts), no falla — sólo log.
"""
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def broadcast_seat_change(*, viaje_id, numero, piso, estado, usuario_id=None):
    """
    estado ∈ {'locked', 'unlocked', 'reserved', 'released'}
    """
    try:
        layer = get_channel_layer()
        if layer is None:
            return
        async_to_sync(layer.group_send)(
            f'viaje_{viaje_id}_asientos',
            {
                'type': 'seat_changed',
                'numero': numero,
                'piso': piso,
                'estado': estado,
                'usuario_id': usuario_id,
            },
        )
    except Exception as exc:  # pragma: no cover
        # Nunca romper la request HTTP por un fallo del broadcast.
        logger.warning('broadcast_seat_change falló: %s', exc)
