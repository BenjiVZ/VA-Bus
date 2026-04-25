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
        fields = ('id', 'nombre', 'placa', 'marca', 'color', 'anio', 'propietario', 'pisos', 'pisos_config', 'capacidad_total', 'disponible', 'motivo_no_disponible')


class AutobusCompactSerializer(serializers.ModelSerializer):
    """Serializer liviano para listados: sin pisos_config ni layout."""
    capacidad_total = serializers.IntegerField(read_only=True)

    class Meta:
        model = Autobus
        fields = ('id', 'nombre', 'placa', 'marca', 'color', 'anio', 'propietario', 'pisos', 'capacidad_total', 'disponible', 'motivo_no_disponible')


class ViajeListSerializer(serializers.ModelSerializer):
    ruta = RutaSerializer(read_only=True)
    autobus = AutobusCompactSerializer(read_only=True)
    asientos_disponibles = serializers.SerializerMethodField()

    class Meta:
        model = Viaje
        fields = ('id', 'ruta', 'autobus', 'tipo_viaje', 'fecha_salida', 'hora_salida',
                  'fecha_vuelta', 'hora_vuelta', 'precio_usd', 'activo',
                  'asientos_disponibles', 'fecha_inicio_venta', 'fecha_fin_venta')

    def get_asientos_disponibles(self, obj):
        # Use pre-computed annotation if available (fast path)
        if hasattr(obj, '_asientos_disponibles'):
            return obj._asientos_disponibles
        if hasattr(obj, '_reservas_activas_count'):
            return obj.autobus.capacidad_total - obj._reservas_activas_count

        # Fallback: single query (for detail views)
        total = obj.autobus.capacidad_total
        from reservas.models import Reserva
        ocupados = Reserva.objects.filter(
            viaje=obj,
            estado__in=['pendiente', 'apartado', 'confirmado']
        ).count()
        return total - ocupados


class ViajeDetailSerializer(serializers.ModelSerializer):
    """Serializer completo con pisos_config (para detalle/asientos)."""
    ruta = RutaSerializer(read_only=True)
    autobus = AutobusSerializer(read_only=True)
    asientos_disponibles = serializers.SerializerMethodField()

    class Meta:
        model = Viaje
        fields = ('id', 'ruta', 'autobus', 'tipo_viaje', 'fecha_salida', 'hora_salida',
                  'fecha_vuelta', 'hora_vuelta', 'precio_usd', 'activo',
                  'asientos_disponibles', 'fecha_inicio_venta', 'fecha_fin_venta')

    def get_asientos_disponibles(self, obj):
        total = obj.autobus.capacidad_total
        from reservas.models import Reserva
        ocupados = Reserva.objects.filter(
            viaje=obj,
            estado__in=['pendiente', 'apartado', 'confirmado']
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
        fields = ('whatsapp_vendedor', 'mensaje_whatsapp', 'nombre_empresa', 'rif', 'domicilio_fiscal', 'banco', 'cuenta_bancaria', 'tipo_cuenta', 'telefono_contacto', 'lema', 'tasa_bcv', 'tasa_actualizada')
