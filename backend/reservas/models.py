from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import uuid


def generar_codigo_ticket():
    """Genera un código de ticket único de 8 caracteres."""
    return uuid.uuid4().hex[:8].upper()


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
    codigo_ticket = models.CharField(
        max_length=8, unique=True, null=True, blank=True,
        verbose_name="Código de Ticket",
        help_text="Se genera automáticamente al confirmar la reserva."
    )
    es_menor_edad = models.BooleanField(
        default=False,
        verbose_name="¿Es menor de edad?"
    )
    para_otra_persona = models.BooleanField(
        default=False,
        verbose_name="¿Asiento para otra persona?"
    )
    nombre_asignado = models.CharField(
        max_length=200, blank=True, default='',
        verbose_name="Nombre del asignado",
        help_text="Nombre de la persona a quien se asigna el asiento"
    )
    cedula_asignado = models.CharField(
        max_length=20, blank=True, default='',
        verbose_name="Cédula del asignado",
        help_text="Cédula de la persona a quien se asigna el asiento"
    )
    viaja_con_animal = models.BooleanField(
        default=False,
        verbose_name="¿Viaja con animal?",
        help_text="Si es verdadero, el pasajero debe presentar la tarjeta de vacunación del animal"
    )
    es_discapacitado = models.BooleanField(
        default=False,
        verbose_name="¿Persona con discapacidad?",
        help_text="Indica si el pasajero de este asiento es una persona con discapacidad"
    )

    def save(self, *args, **kwargs):
        if not self.pk and not self.fecha_expiracion:
            self.fecha_expiracion = timezone.now() + timedelta(minutes=15)
        # Auto-generate ticket code when confirmed
        if self.estado == 'confirmado' and not self.codigo_ticket:
            self.codigo_ticket = generar_codigo_ticket()
        super().save(*args, **kwargs)

    @property
    def esta_expirada(self):
        if self.estado != 'pendiente':
            return False
        if self.fecha_expiracion and timezone.now() > self.fecha_expiracion:
            return True
        return False

    @classmethod
    def limpiar_expiradas(cls, viaje=None):
        """
        Cancela automáticamente todas las reservas pendientes que ya expiraron.
        Si se pasa un viaje, solo limpia las de ese viaje.
        Retorna la cantidad de reservas canceladas.
        """
        filtro = cls.objects.filter(
            estado='pendiente',
            fecha_expiracion__lt=timezone.now()
        )
        if viaje:
            filtro = filtro.filter(viaje=viaje)
        return filtro.update(estado='cancelado')

    class Meta:
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Reserva #{self.pk} - Asiento {self.numero_asiento} (Piso {self.piso_asiento}) - {self.get_estado_display()}"


class BloqueoAsiento(models.Model):
    """Bloqueo temporal de asiento mientras el usuario completa la compra."""
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bloqueos_asiento',
        verbose_name="Usuario"
    )
    viaje = models.ForeignKey(
        'viajes.Viaje',
        on_delete=models.CASCADE,
        related_name='bloqueos_asiento',
        verbose_name="Viaje"
    )
    numero_asiento = models.PositiveIntegerField(verbose_name="Número de Asiento")
    piso_asiento = models.PositiveIntegerField(default=1, verbose_name="Piso del Asiento")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Creación")
    fecha_expiracion = models.DateTimeField(verbose_name="Fecha de Expiración")

    @property
    def esta_expirado(self):
        return timezone.now() >= self.fecha_expiracion

    @classmethod
    def limpiar_expirados(cls, viaje=None):
        qs = cls.objects.filter(fecha_expiracion__lt=timezone.now())
        if viaje:
            qs = qs.filter(viaje=viaje)
        deleted_count, _ = qs.delete()
        return deleted_count

    class Meta:
        verbose_name = "Bloqueo de Asiento"
        verbose_name_plural = "Bloqueos de Asientos"
        ordering = ['-fecha_creacion']
        unique_together = [('viaje', 'numero_asiento', 'piso_asiento')]

    def __str__(self):
        return f"Bloqueo {self.viaje_id} - Asiento {self.numero_asiento} (Piso {self.piso_asiento})"
