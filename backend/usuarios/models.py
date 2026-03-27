from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    cedula = models.CharField(max_length=20, blank=True, null=True, verbose_name="Cédula")
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    fecha_nacimiento = models.DateField(blank=True, null=True, verbose_name="Fecha de Nacimiento")

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self):
        return f"{self.get_full_name() or self.username}"
