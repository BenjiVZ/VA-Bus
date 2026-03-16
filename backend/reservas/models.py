from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import uuid


class Reserva(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('apartado', 'Apartado'),
        ('confirmado', 'Confirmado'),
        ('cancelado', 'Cancelado'),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reservas',
        verbose_name="Usuario"
    )
    viaje = models.ForeignKey(
        'viajes.Viaje',
        on_delete=models.CASCADE,
        related_name='reservas',
        verbose_name="Viaje"
    )
    numero_asiento = models.PositiveIntegerField(verbose_name="Número de Asiento")
    piso_asiento = models.PositiveIntegerField(default=1, verbose_name="Piso del Asiento")
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente',
        verbose_name="Estado"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_actualizacion = models.DateTimeField(auto_now=True, verbose_name="Última Actualización")
    nombre_pasajero = models.CharField(max_length=200, blank=True, verbose_name="Nombre del Pasajero")
    cedula_pasajero = models.CharField(max_length=20, blank=True, verbose_name="Cédula del Pasajero")
    grupo_pago = models.UUIDField(
        null=True, blank=True, db_index=True,
        verbose_name="Grupo de Pago",
        help_text="UUID que agrupa las reservas de una misma compra"
    )
    fecha_expiracion = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Fecha de Expiración",
        help_text="15 min después de creación. Solo aplica en estado pendiente."
    )

    def save(self, *args, **kwargs):
        if not self.pk and not self.fecha_expiracion:
            self.fecha_expiracion = timezone.now() + timedelta(minutes=15)
        super().save(*args, **kwargs)

    @property
    def esta_expirada(self):
        if self.estado != 'pendiente':
            return False
        if self.fecha_expiracion and timezone.now() > self.fecha_expiracion:
            return True
        return False

    class Meta:
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"
        unique_together = ('viaje', 'numero_asiento', 'piso_asiento')
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Reserva #{self.pk} - Asiento {self.numero_asiento} (Piso {self.piso_asiento}) - {self.get_estado_display()}"
