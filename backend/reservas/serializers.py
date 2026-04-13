from rest_framework import serializers
from .models import Reserva


class ReservaSerializer(serializers.ModelSerializer):
    viaje_info = serializers.SerializerMethodField()
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = Reserva
        fields = (
            'id', 'viaje', 'numero_asiento', 'piso_asiento',
            'estado', 'estado_display', 'nombre_pasajero', 'cedula_pasajero',
            'es_menor_edad', 'para_otra_persona', 'nombre_asignado', 'cedula_asignado',
            'viaja_con_animal', 'es_discapacitado',
            'fecha_creacion', 'fecha_actualizacion', 'viaje_info', 'grupo_pago'
        )
        read_only_fields = ('id', 'estado', 'fecha_creacion', 'fecha_actualizacion')

    def get_viaje_info(self, obj):
        viaje = obj.viaje
        return {
            'id': viaje.id,
            'origen': viaje.ruta.origen,
            'destino': viaje.ruta.destino,
            'fecha_salida': viaje.fecha_salida,
            'hora_salida': viaje.hora_salida,
            'precio_usd': float(viaje.precio_usd),
            'autobus': viaje.autobus.nombre
        }


class CrearReservaSerializer(serializers.Serializer):
    viaje_id = serializers.IntegerField()
    asientos = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        help_text="Lista de asientos: [{'numero': 1, 'piso': 1, 'es_menor': false, 'para_otra': false, 'nombre_asignado': '', 'cedula_asignado': '', 'viaja_con_animal': false}, ...]"
    )
    nombre_pasajero = serializers.CharField(max_length=200, required=False, default='')
    cedula_pasajero = serializers.CharField(max_length=20, required=False, default='')


class AdminReservaSerializer(serializers.ModelSerializer):
    """Serializer con info de usuario para panel de admin."""
    viaje_info = serializers.SerializerMethodField()
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    usuario_info = serializers.SerializerMethodField()

    class Meta:
        model = Reserva
        fields = (
            'id', 'viaje', 'numero_asiento', 'piso_asiento',
            'estado', 'estado_display', 'nombre_pasajero', 'cedula_pasajero',
            'es_menor_edad', 'para_otra_persona', 'nombre_asignado', 'cedula_asignado',
            'viaja_con_animal', 'es_discapacitado',
            'fecha_creacion', 'fecha_actualizacion', 'viaje_info', 'usuario_info'
        )

    def get_viaje_info(self, obj):
        viaje = obj.viaje
        return {
            'id': viaje.id,
            'origen': viaje.ruta.origen,
            'destino': viaje.ruta.destino,
            'fecha_salida': viaje.fecha_salida,
            'hora_salida': viaje.hora_salida,
            'precio_usd': float(viaje.precio_usd),
            'autobus': viaje.autobus.nombre
        }

    def get_usuario_info(self, obj):
        u = obj.usuario
        return {
            'id': u.id,
            'username': u.username,
            'nombre': u.get_full_name() or u.username,
            'email': u.email,
            'cedula': getattr(u, 'cedula', ''),
            'telefono': getattr(u, 'telefono', ''),
        }
