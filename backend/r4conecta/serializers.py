import re
from rest_framework import serializers

from .bancos import CODIGOS_VALIDOS

CEDULA_RE = re.compile(r'^[VEJPvejp]\d{6,9}$')


class GenerarOtpSerializer(serializers.Serializer):
    """Datos para iniciar un débito inmediato (paso 1: generar OTP)."""
    grupo_pago = serializers.UUIDField()
    banco = serializers.RegexField(r'^\d{4}$', error_messages={
        'invalid': 'El código de banco debe tener 4 dígitos.'})
    cedula = serializers.CharField(max_length=12)
    telefono = serializers.RegexField(r'^\d{11}$', error_messages={
        'invalid': 'El teléfono debe tener 11 dígitos.'})
    nombre = serializers.CharField(max_length=40, required=False, allow_blank=True, default='')
    concepto = serializers.CharField(max_length=30, required=False, allow_blank=True, default='')

    def validate_banco(self, value):
        if value not in CODIGOS_VALIDOS:
            raise serializers.ValidationError("Código de banco no reconocido.")
        return value

    def validate_cedula(self, value):
        value = value.strip().upper()
        if not CEDULA_RE.match(value):
            raise serializers.ValidationError(
                "Cédula inválida. Formato: letra (V/E/J/P) + 6 a 9 dígitos.")
        return value


class ConfirmarDebitoSerializer(serializers.Serializer):
    """Datos para completar el débito (paso 2: confirmar con OTP)."""
    operacion_id = serializers.IntegerField()
    otp = serializers.RegexField(r'^\d{1,8}$', error_messages={
        'invalid': 'El OTP debe ser numérico (hasta 8 dígitos).'})
