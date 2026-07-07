from django.db import models
from django.contrib.auth import get_user_model
from decimal import Decimal
import uuid

User = get_user_model()


class OperacionDebitoOTP(models.Model):
    ESTADO_CHOICES = [
        ("otp_generado", "OTP Generado"),
        ("procesando", "Procesando (débito en curso)"),
        ("en_espera", "En Espera (AC00)"),
        ("aceptada", "Aceptada (ACCP)"),
        ("rechazada", "Rechazada"),
        ("error", "Error"),
    ]

    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    grupo_pago = models.UUIDField(db_index=True, help_text="UUID del grupo de reserva")
    banco = models.CharField(max_length=4, help_text="Código del banco (ej: 0192)")
    cedula = models.CharField(max_length=20)
    telefono = models.CharField(max_length=20)
    nombre = models.CharField(max_length=200)
    monto = models.DecimalField(max_digits=10, decimal_places=2, help_text="Monto en bolívares")
    concepto = models.CharField(max_length=30, blank=True, default="pago")

    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="otp_generado")
    code = models.CharField(max_length=10, blank=True, help_text="Código de respuesta del banco")
    mensaje = models.TextField(blank=True, help_text="Mensaje de respuesta del banco")
    referencia = models.CharField(max_length=100, blank=True, help_text="Referencia de la transacción")
    operacion_id = models.CharField(max_length=50, blank=True, db_index=True, help_text="ID de operación del banco")

    otp_response = models.JSONField(blank=True, null=True, help_text="Respuesta cruda de GenerarOtp")
    debito_response = models.JSONField(blank=True, null=True, help_text="Respuesta cruda de DebitoInmediato")
    consulta_response = models.JSONField(blank=True, null=True, help_text="Respuesta cruda de ConsultarOperaciones")
    comprobante = models.ImageField(blank=True, null=True, upload_to='comprobantes/r4/%Y/%m/', verbose_name="Comprobante (opcional)")

    created_at = models.DateTimeField(auto_now_add=True, null=True, verbose_name="Creado")
    updated_at = models.DateTimeField(auto_now=True, null=True, verbose_name="Actualizado")

    class Meta:
        verbose_name = "Operación Débito OTP"
        verbose_name_plural = "Operaciones Débito OTP"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.banco} - {self.cedula} - {self.estado} ({self.id})"
