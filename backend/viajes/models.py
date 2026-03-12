from django.db import models
from django.core.validators import MinValueValidator


class Ruta(models.Model):
    origen = models.CharField(max_length=100, verbose_name="Origen")
    destino = models.CharField(max_length=100, verbose_name="Destino")
    duracion_estimada = models.CharField(max_length=50, blank=True, verbose_name="Duración Estimada")

    class Meta:
        verbose_name = "Ruta"
        verbose_name_plural = "Rutas"
        unique_together = ('origen', 'destino')

    def __str__(self):
        return f"{self.origen} → {self.destino}"


class Autobus(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre / Identificador")
    placa = models.CharField(max_length=20, unique=True, verbose_name="Placa")
    pisos = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)], verbose_name="Cantidad de Pisos")

    class Meta:
        verbose_name = "Autobús"
        verbose_name_plural = "Autobuses"

    def __str__(self):
        return f"{self.nombre} ({self.placa})"

    @property
    def capacidad_total(self):
        total = 0
        for piso in self.pisos_config.all():
            total += piso.capacidad
        return total


class PisoAutobus(models.Model):
    autobus = models.ForeignKey(Autobus, on_delete=models.CASCADE, related_name='pisos_config', verbose_name="Autobús")
    numero_piso = models.PositiveIntegerField(default=1, verbose_name="Número de Piso")
    filas = models.PositiveIntegerField(default=10, verbose_name="Filas de la Grilla")
    columnas = models.PositiveIntegerField(default=5, verbose_name="Columnas de la Grilla")
    layout = models.JSONField(
        default=list, blank=True,
        verbose_name="Layout de Asientos",
        help_text="Grilla 2D: cada celda tiene type (seat/door/empty/aisle/stairs) y number (para asientos)"
    )

    class Meta:
        verbose_name = "Piso de Autobús"
        verbose_name_plural = "Pisos de Autobús"
        unique_together = ('autobus', 'numero_piso')
        ordering = ['numero_piso']

    def __str__(self):
        return f"Piso {self.numero_piso} - {self.autobus.nombre}"

    @property
    def capacidad(self):
        count = 0
        for row in (self.layout or []):
            for cell in row:
                if isinstance(cell, dict) and cell.get('type') == 'seat':
                    count += 1
        return count


class Viaje(models.Model):
    ruta = models.ForeignKey(Ruta, on_delete=models.CASCADE, related_name='viajes', verbose_name="Ruta")
    autobus = models.ForeignKey(Autobus, on_delete=models.CASCADE, related_name='viajes', verbose_name="Autobús")
    fecha_salida = models.DateField(verbose_name="Fecha de Salida")
    hora_salida = models.TimeField(verbose_name="Hora de Salida")
    precio_usd = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio (USD)")
    activo = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Viaje"
        verbose_name_plural = "Viajes"
        ordering = ['fecha_salida', 'hora_salida']

    def __str__(self):
        return f"{self.ruta} - {self.fecha_salida} {self.hora_salida}"


class ConfiguracionGeneral(models.Model):
    """Modelo singleton para configuración general del sistema."""
    whatsapp_vendedor = models.CharField(
        max_length=20,
        verbose_name="WhatsApp del Vendedor",
        help_text="Número en formato internacional, ej: 584121234567"
    )
    mensaje_whatsapp = models.TextField(
        default="Hola, quiero confirmar mi reserva de autobús:\n\n{detalles}",
        verbose_name="Plantilla de Mensaje WhatsApp",
        help_text="Usa {detalles} donde quieras insertar la info de la reserva"
    )
    nombre_empresa = models.CharField(max_length=200, default="Aerorutas de Venezuela", verbose_name="Nombre de la Empresa")
    tasa_bcv = models.DecimalField(
        max_digits=12, decimal_places=4, default=0,
        verbose_name="Tasa BCV (Bs/$)"
    )
    tasa_actualizada = models.DateTimeField(null=True, blank=True, verbose_name="Última Actualización de Tasa")

    class Meta:
        verbose_name = "Configuración General"
        verbose_name_plural = "Configuración General"

    def __str__(self):
        return "Configuración General"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
