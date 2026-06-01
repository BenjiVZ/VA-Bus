"""
Consumers de WebSocket para la app viajes.

AsientosConsumer escucha en /ws/viajes/<viaje_id>/asientos/ y mantiene un
grupo por viaje. Las vistas REST emiten eventos al grupo cuando cambia
la disponibilidad de un asiento, así todos los clientes conectados al
mismo viaje se actualizan sin polling.

Formato de eventos enviados al cliente:
    {
        "type": "seat_changed",
        "numero": 12,
        "piso": 1,
        "estado": "locked" | "unlocked" | "reserved" | "released",
        "usuario_id": 42 | None,   # quién originó el cambio (para que el cliente lo ignore si fue él)
    }
"""
from channels.generic.websocket import AsyncJsonWebsocketConsumer


class AsientosConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.viaje_id = self.scope['url_route']['kwargs']['viaje_id']
        self.group_name = f'viaje_{self.viaje_id}_asientos'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        # Aún si no nos conectamos completamente, intentar limpiar.
        group = getattr(self, 'group_name', None)
        if group:
            await self.channel_layer.group_discard(group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        # El cliente no necesita mandar nada; sólo escucha. Si manda, lo ignoramos.
        return

    # Handler invocado cuando una vista hace group_send(type='seat_changed', ...)
    async def seat_changed(self, event):
        await self.send_json({
            'type': 'seat_changed',
            'numero': event['numero'],
            'piso': event['piso'],
            'estado': event['estado'],
            'usuario_id': event.get('usuario_id'),
        })
