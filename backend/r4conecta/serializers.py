from rest_framework import serializers
import re


class GenerarOtpSerializer(serializers.Serializer):
    """Valida los datos para generar un OTP."""
    grupo_pago = serializers.UUIDField(help_text="UUID del grupo de reserva")
    banco = serializers.CharField(max_length=4, help_text="Código banco (4 dígitos)")
    cedula = serializers.CharField(max_length=20, help_text="Cédula (ej: V12345678)")
    telefono = serializers.CharField(max_length=20, help_text="Teléfono (11 dígitos)")
    concepto = serializers.CharField(max_length=30, required=False, default="Boletos Aerorutas")

    def validate_banco(self, value):
        if not re.match(r'^\d{4}$', value):
            raise serializers.ValidationError("Banco debe ser 4 dígitos numéricos")
        return value

    def validate_cedula(self, value):
        if not re.match(r'^[VEJPvejp]\d{6,9}$', value):
            raise serializers.ValidationError("Cédula inválida (ej: V12345678)")
        return value.upper()

    def validate_telefono(self, value):
        digits = re.sub(r'\D', '', value)
        if len(digits) != 11:
            raise serializers.ValidationError("Teléfono debe tener 11 dígitos")
        return digits

    def validate_concepto(self, value):
        if len(value) > 30:
            raise serializers.ValidationError("Concepto máximo 30 caracteres")
        return value


class ConfirmarDebitoSerializer(serializers.Serializer):
    """Valida los datos para confirmar el débito con OTP."""
    operacion_id = serializers.IntegerField(help_text="ID de la operación de débito")
    otp = serializers.CharField(max_length=8, help_text="Código OTP de 8 dígitos")

    def validate_otp(self, value):
        if not re.match(r'^\d{8}$', value):
            raise serializers.ValidationError("OTP debe ser 8 dígitos")
        return value
