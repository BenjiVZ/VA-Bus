from rest_framework import serializers
from .models import Ruta, Autobus, PisoAutobus, Viaje, ConfiguracionGeneral


class RutaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ruta
        fields = '__all__'


class PisoAutobusSerializer(serializers.ModelSerializer):
    capacidad = serializers.ReadOnlyField()

    class Meta:
        model = PisoAutobus
        fields = ('id', 'numero_piso', 'filas', 'columnas', 'layout', 'capacidad')


class AutobusSerializer(serializers.ModelSerializer):
    pisos_config = PisoAutobusSerializer(many=True, read_only=True)
    capacidad_total = serializers.ReadOnlyField()

    class Meta:
        model = Autobus
        fields = ('id', 'nombre', 'placa', 'pisos', 'pisos_config', 'capacidad_total')


class ViajeListSerializer(serializers.ModelSerializer):
    ruta = RutaSerializer(read_only=True)
    autobus = AutobusSerializer(read_only=True)
    asientos_disponibles = serializers.SerializerMethodField()

    class Meta:
        model = Viaje
        fields = ('id', 'ruta', 'autobus', 'fecha_salida', 'hora_salida',
                  'precio_usd', 'activo', 'asientos_disponibles')

    def get_asientos_disponibles(self, obj):
        total = obj.autobus.capacidad_total
        from reservas.models import Reserva
        ocupados = Reserva.objects.filter(
            viaje=obj,
            estado__in=['pendiente', 'confirmado']
        ).count()
        return total - ocupados


class AsientoMapSerializer(serializers.Serializer):
    """Genera el mapa de asientos para un viaje dado."""
    piso = serializers.IntegerField()
    numero = serializers.IntegerField()
    fila = serializers.IntegerField()
    columna = serializers.IntegerField()
    posicion = serializers.CharField()  # izquierda, derecha, fondo
    disponible = serializers.BooleanField()
    tipo = serializers.CharField()  # ventana, pasillo


class ConfiguracionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConfiguracionGeneral
        fields = ('whatsapp_vendedor', 'mensaje_whatsapp', 'nombre_empresa',
                  'tasa_bcv', 'tasa_actualizada')
