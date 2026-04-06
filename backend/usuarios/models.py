from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import random


class Usuario(AbstractUser):
    cedula = models.CharField(max_length=20, blank=True, null=True, verbose_name="Cédula")
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    fecha_nacimiento = models.DateField(blank=True, null=True, verbose_name="Fecha de Nacimiento")
    email_verificado = models.BooleanField(default=False, verbose_name="Email Verificado")
    codigo_verificacion = models.CharField(
        max_length=6, blank=True, null=True,
        verbose_name="Código de Verificación"
    )
    codigo_verificacion_expira = models.DateTimeField(
        blank=True, null=True,
        verbose_name="Expiración del Código"
    )

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self):
        return f"{self.get_full_name() or self.username}"

    def generar_codigo(self, minutos=15):
        """Genera un código de 6 dígitos con expiración."""
        self.codigo_verificacion = f"{random.randint(100000, 999999)}"
        self.codigo_verificacion_expira = timezone.now() + timezone.timedelta(minutes=minutos)
        self.save(update_fields=['codigo_verificacion', 'codigo_verificacion_expira'])
        return self.codigo_verificacion

    def verificar_codigo(self, codigo):
        """Verifica si el código es correcto y no ha expirado."""
        if not self.codigo_verificacion or not self.codigo_verificacion_expira:
            return False
        if self.codigo_verificacion != codigo:
            return False
        if timezone.now() > self.codigo_verificacion_expira:
            return False
        return True

    def limpiar_codigo(self):
        """Limpia el código después de usarlo."""
        self.codigo_verificacion = None
        self.codigo_verificacion_expira = None
        self.save(update_fields=['codigo_verificacion', 'codigo_verificacion_expira'])

