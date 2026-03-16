from rest_framework import serializers
from .models import MetodoPago, DatoMetodoPago, ComprobantePago


class DatoMetodoPagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatoMetodoPago
        fields = ('id', 'etiqueta', 'valor', 'orden')


class MetodoPagoSerializer(serializers.ModelSerializer):
    datos = DatoMetodoPagoSerializer(many=True, read_only=True)

    class Meta:
        model = MetodoPago
        fields = ('id', 'nombre', 'moneda', 'descripcion', 'datos')


class ComprobantePagoSerializer(serializers.ModelSerializer):
    metodo_pago_nombre = serializers.CharField(
        source='metodo_pago.nombre', read_only=True
    )
    estado_display = serializers.CharField(
        source='get_estado_display', read_only=True
    )

    class Meta:
        model = ComprobantePago
        fields = (
            'id', 'grupo_pago', 'metodo_pago', 'metodo_pago_nombre',
            'numero_referencia', 'imagen', 'monto', 'moneda',
            'estado', 'estado_display', 'fecha_creacion',
            'fecha_revision', 'nota_admin'
        )
        read_only_fields = (
            'id', 'estado', 'fecha_creacion', 'fecha_revision', 'nota_admin'
        )


class CrearComprobanteSerializer(serializers.Serializer):
    grupo_pago = serializers.UUIDField()
    metodo_pago_id = serializers.IntegerField()
    numero_referencia = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    imagen = serializers.ImageField()
    monto = serializers.DecimalField(max_digits=12, decimal_places=2)
    moneda = serializers.CharField(max_length=3, required=False, default='BS')


class AdminComprobanteSerializer(serializers.ModelSerializer):
    """Serializer con info completa para el admin."""
    metodo_pago_nombre = serializers.CharField(
        source='metodo_pago.nombre', read_only=True
    )
    estado_display = serializers.CharField(
        source='get_estado_display', read_only=True
    )
    usuario_info = serializers.SerializerMethodField()
    reservas_info = serializers.SerializerMethodField()

    class Meta:
        model = ComprobantePago
        fields = (
            'id', 'grupo_pago', 'metodo_pago', 'metodo_pago_nombre',
            'numero_referencia', 'imagen', 'monto', 'moneda',
            'estado', 'estado_display', 'fecha_creacion',
            'fecha_revision', 'nota_admin', 'revisado_por',
            'usuario_info', 'reservas_info'
        )

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

    def get_reservas_info(self, obj):
        from reservas.models import Reserva
        reservas = Reserva.objects.filter(
            grupo_pago=obj.grupo_pago
        ).select_related('viaje', 'viaje__ruta')
        return [{
            'id': r.id,
            'asiento': r.numero_asiento,
            'piso': r.piso_asiento,
            'estado': r.estado,
            'nombre_pasajero': r.nombre_pasajero,
            'ruta': f"{r.viaje.ruta.origen} → {r.viaje.ruta.destino}" if r.viaje else '',
            'fecha': str(r.viaje.fecha_salida) if r.viaje else '',
        } for r in reservas]
