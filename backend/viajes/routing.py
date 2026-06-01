"""
WebSocket URL patterns para la app viajes.

Endpoint:
  ws://host/ws/viajes/<viaje_id>/asientos/

Cada viaje tiene su propio "grupo" de Channels. Las vistas REST
(bloquear, liberar, crear reserva, validar comprobante) hacen broadcast
al grupo correspondiente cuando un asiento cambia de estado.
"""
from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(
        r'ws/viajes/(?P<viaje_id>\d+)/asientos/$',
        consumers.AsientosConsumer.as_asgi(),
    ),
]
