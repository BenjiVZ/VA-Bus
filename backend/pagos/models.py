from django.db import models
from django.conf import settings
import uuid


class MetodoPago(models.Model):
    """Método de pago configurable desde Django Admin."""
    MONEDA_CHOICES = [
        ('BS', 'Bolívares'),
        ('USD', 'Dólares'),
    ]

    TIPO_CHOICES = [
        ('transferencia', 'Transferencia Bancaria'),
        ('pago_movil', 'Pago Móvil'),
        ('divisas', 'Divisas (Efectivo)'),
        ('zinli', 'Zinli'),
        ('zelle', 'Zelle'),
        ('binance', 'Binance'),
        ('cobro_inmediato', 'Cobro Inmediato (Débito OTP)'),
        ('otro', 'Otro'),
    ]

    nombre = models.CharField(max_length=100, verbose_name="Nombre del Método")
    tipo = models.CharField(
        max_length=20, choices=TIPO_CHOICES, default='transferencia',
        verbose_name="Tipo de método",
        help_text="Categoría del método de pago"
    )
    moneda = models.CharField(
        max_length=3, choices=MONEDA_CHOICES, default='BS',
        verbose_name="Moneda",
        help_text="Determina si el monto se muestra en Bs o USD"
    )
    descripcion = models.CharField(
        max_length=200, blank=True,
        verbose_name="Badge / Descripción corta",
        help_text="Ej: 'Se acredita más rápido'. Aparece como badge debajo del nombre."
    )
    requiere_foto_billete = models.BooleanField(
        default=False,
        verbose_name="¿Requiere foto del billete?",
        help_text="Si es pago en divisas/efectivo, el cliente debe subir foto del billete"
    )
    activo = models.BooleanField(default=True, verbose_name="Activo")
    orden = models.PositiveIntegerField(default=0, verbose_name="Orden de aparición")

    class Meta:
        verbose_name = "Método de Pago"
        verbose_name_plural = "Métodos de Pago"
        ordering = ['orden', 'nombre']

    def __str__(self):
        return f"{self.nombre} ({self.get_moneda_display()})"


class DatoMetodoPago(models.Model):
    """Campos copiables que se muestran al usuario para un método de pago."""
    metodo_pago = models.ForeignKey(
        MetodoPago, on_delete=models.CASCADE,
        related_name='datos',
        verbose_name="Método de Pago"
    )
    etiqueta = models.CharField(
        max_length=100, verbose_name="Etiqueta",
        help_text="Ej: 'Banco', 'RIF', 'Teléfono', 'Email'"
    )
    valor = models.CharField(
        max_length=300, verbose_name="Valor",
        help_text="Ej: 'Banco Nacional de Crédito', 'J-313189260'"
    )
    orden = models.PositiveIntegerField(default=0, verbose_name="Orden")

    class Meta:
        verbose_name = "Dato del Método"
        verbose_name_plural = "Datos del Método"
        ordering = ['orden']

    def __str__(self):
        return f"{self.etiqueta}: {self.valor}"


class ComprobantePago(models.Model):
    """Comprobante subido por el cliente para validación del admin."""
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente de revisión'),
        ('aprobado', 'Aprobado'),
        ('rechazado', 'Rechazado'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    grupo_pago = models.UUIDField(
        verbose_name="Grupo de Pago",
        help_text="UUID que agrupa las reservas de una misma compra",
        db_index=True
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comprobantes',
        verbose_name="Usuario"
    )
    metodo_pago = models.ForeignKey(
        MetodoPago, on_delete=models.SET_NULL,
        null=True, related_name='comprobantes',
        verbose_name="Método de Pago"
    )
    numero_referencia = models.CharField(
        max_length=100, blank=True,
        verbose_name="Número de Referencia / Comprobante",
        help_text="Opcional pero recomendado"
    )
    imagen = models.ImageField(
        upload_to='comprobantes/%Y/%m/',
        verbose_name="Captura del Pago"
    )
    foto_billete = models.ImageField(
        upload_to='comprobantes/billetes/%Y/%m/',
        null=True, blank=True,
        verbose_name="Foto del billete",
        help_text="Requerida cuando el pago es en divisas/efectivo"
    )
    monto = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name="Monto pagado"
    )
    moneda = models.CharField(max_length=3, default='BS', verbose_name="Moneda del monto")
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES,
        default='pendiente', verbose_name="Estado"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de envío")
    fecha_revision = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de revisión")
    revisado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='comprobantes_revisados',
        verbose_name="Revisado por"
    )
    nota_admin = models.TextField(
        blank=True,
        verbose_name="Nota del administrador",
        help_text="Motivo de rechazo u observaciones"
    )

    class Meta:
        verbose_name = "Comprobante de Pago"
        verbose_name_plural = "Comprobantes de Pago"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Comprobante {self.id} — {self.get_estado_display()}"
