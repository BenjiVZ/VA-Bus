from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.password_validation import validate_password
from .models import Usuario


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'cedula', 'telefono', 'fecha_nacimiento', 'is_staff', 'email_verificado')
        read_only_fields = ('id',)


class RegistroSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password2 = serializers.CharField(write_only=True, min_length=6)
    email = serializers.EmailField(required=True)

    class Meta:
        model = Usuario
        fields = ('username', 'email', 'password', 'password2', 'first_name', 'last_name', 'cedula', 'telefono', 'fecha_nacimiento')

    def validate_email(self, value):
        # Sin esto se crean cuentas duplicadas y TODOS los flujos que buscan
        # por email (login por email, reset, reenviar código) explotan con 500.
        if Usuario.objects.filter(email__iexact=value.strip()).exists():
            raise serializers.ValidationError(
                'Ya existe una cuenta registrada con este email. '
                'Inicia sesión o usa "¿Olvidaste tu contraseña?".')
        return value.strip()

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password2": "Las contraseñas no coinciden."})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        user = Usuario(**validated_data)
        user.set_password(password)
        user.save()
        return user


class AdminClienteSerializer(serializers.ModelSerializer):
    total_viajes = serializers.IntegerField(read_only=True, default=0)
    ultimo_viaje = serializers.DateField(read_only=True, default=None)

    class Meta:
        model = Usuario
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'cedula', 'telefono', 'fecha_nacimiento',
            'es_vip', 'servicio_vip', 'notas_admin',
            'date_joined', 'total_viajes', 'ultimo_viaje',
        )
        read_only_fields = ('id', 'username', 'email', 'date_joined')

