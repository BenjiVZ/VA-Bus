from django.db import models
from django.conf import settings


class OperacionDebitoOTP(models.Model):
    """
    Registro de una operación de Débito Inmediato (OTP) contra R4 Conecta.

    Sirve de auditoría y soporta el caso AC00 (operación en espera, que luego se
    resuelve con ConsultarOperaciones usando `operacion_id`).

    Importante: NUNCA se almacena el OTP enviado por el cliente.
    """

    ESTADO_CHOICES = [
        ('otp_generado', 'OTP generado'),
        ('en_espera', 'En espera del receptor (AC00)'),
        ('aceptada', 'Aceptada (ACCP)'),
        ('rechazada', 'Rechazada'),
        ('error', 'Error de comunicación'),
    ]

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='operaciones_debito_otp',
        verbose_name="Usuario",
    )
    grupo_pago = models.UUIDField(
        null=True, blank=True, db_index=True,
        verbose_name="Grupo de Pago",
        help_text="UUID de las reservas asociadas a este cobro.",
    )

    # ── Datos del pagador (cliente) ──
    banco = models.CharField(max_length=4, verbose_name="Código de Banco")
    cedula = models.CharField(max_length=12, verbose_name="Cédula")
    telefono = models.CharField(max_length=11, verbose_name="Teléfono")
    nombre = models.CharField(max_length=40, blank=True, verbose_name="Nombre")
    monto = models.DecimalField(
        max_digits=12, decimal_places=2,
        verbose_name="Monto (Bs)",
    )
    concepto = models.CharField(max_length=30, blank=True, verbose_name="Concepto")

    # Comprobante opcional que el cliente puede adjuntar al confirmar el OTP.
    comprobante = models.ImageField(
        upload_to='comprobantes/r4/%Y/%m/',
        null=True, blank=True,
        verbose_name="Comprobante (opcional)",
    )

    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES, default='otp_generado',
        db_index=True, verbose_name="Estado",
    )

    # ── Respuesta del banco ──
    code = models.CharField(max_length=10, blank=True, verbose_name="Código del banco")
    mensaje = models.CharField(max_length=255, blank=True, verbose_name="Mensaje del banco")
    referencia = models.CharField(max_length=30, blank=True, verbose_name="Referencia")
    operacion_id = models.CharField(
        max_length=36, blank=True,
        verbose_name="Id de operación (banco)",
        help_text="UUID devuelto por el banco; se usa para ConsultarOperaciones.",
    )

    # ── Auditoría (respuestas crudas, sin el OTP) ──
    otp_response = models.JSONField(null=True, blank=True, verbose_name="Respuesta GenerarOtp")
    debito_response = models.JSONField(null=True, blank=True, verbose_name="Respuesta DebitoInmediato")
    consulta_response = models.JSONField(null=True, blank=True, verbose_name="Respuesta ConsultarOperaciones")

    creado = models.DateTimeField(auto_now_add=True, verbose_name="Creado")
    actualizado = models.DateTimeField(auto_now=True, verbose_name="Actualizado")

    class Meta:
        verbose_name = "Operación Débito OTP"
        verbose_name_plural = "Operaciones Débito OTP"
        ordering = ['-creado']

    def __str__(self):
        return f"DébitoOTP #{self.pk} - {self.cedula} - {self.get_estado_display()}"
