from django.db import models
from django.core.validators import MinValueValidator


class Oficina(models.Model):
    """
    Oficina / sucursal / terminal de Aerorutas.
    Es un lugar físico de donde salen y a donde llegan los autobuses.
    Sincronizable con el sistema externo de la empresa
    (endpoint OFICINAS de aerorutasdevenezuela.com).
    """
    codofi = models.CharField(
        max_length=10, unique=True, verbose_name="Código (codofi)",
        help_text="Código numérico único de la oficina. Ej: '01', '04', '100'"
    )
    desofi = models.CharField(
        max_length=100, verbose_name="Nombre (desofi)",
        help_text="Nombre completo. Ej: 'CARACAS LA BANDERA'"
    )
    siglas = models.CharField(
        max_length=10, blank=True, default='',
        verbose_name="Siglas",
        help_text="Siglas cortas. Ej: 'CCS', 'MBO', 'MRD'"
    )
    estado = models.CharField(
        max_length=50, blank=True, default='',
        verbose_name="Estado",
        help_text="Estado venezolano. Ej: 'Distrito Capital', 'Zulia'"
    )
    ciudad = models.CharField(
        max_length=100, blank=True, default='',
        verbose_name="Ciudad",
        help_text="Ciudad donde está ubicada (para el mapa). Si está vacío se infiere de desofi."
    )
    latitud = models.DecimalField(
        max_digits=10, decimal_places=6,
        null=True, blank=True,
        verbose_name="Latitud"
    )
    longitud = models.DecimalField(
        max_digits=10, decimal_places=6,
        null=True, blank=True,
        verbose_name="Longitud"
    )
    activa = models.BooleanField(default=True, verbose_name="Activa")
    fecha_sincronizacion = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Última sincronización"
    )

    class Meta:
        verbose_name = "Oficina"
        verbose_name_plural = "Oficinas"
        ordering = ['desofi']

    def __str__(self):
        return f"{self.desofi} ({self.siglas or self.codofi})"


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
    marca = models.CharField(max_length=50, blank=True, default='', verbose_name="Marca")
    color = models.CharField(max_length=50, blank=True, default='', verbose_name="Color")
    anio = models.PositiveIntegerField(null=True, blank=True, verbose_name="Año")
    propietario = models.CharField(max_length=200, blank=True, default='', verbose_name="Propietario")
    pisos = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)], verbose_name="Cantidad de Pisos")
    disponible = models.BooleanField(
        default=True,
        verbose_name="Disponible",
        help_text="Desmarcar si el autobús no está operativo."
    )
    motivo_no_disponible = models.CharField(
        max_length=300, blank=True, default='',
        verbose_name="Motivo de no disponibilidad",
        help_text="Ej: En mantenimiento, avería mecánica, revisión técnica, etc."
    )

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
    TIPO_CHOICES = [
        ('ida', 'Solo Ida'),
        ('ida_vuelta', 'Ida y Vuelta'),
    ]

    ruta = models.ForeignKey(Ruta, on_delete=models.CASCADE, related_name='viajes', verbose_name="Ruta")
    autobus = models.ForeignKey(Autobus, on_delete=models.CASCADE, related_name='viajes', verbose_name="Autobús")
    tipo_viaje = models.CharField(
        max_length=15, choices=TIPO_CHOICES, default='ida',
        verbose_name="Tipo de Viaje"
    )
    fecha_salida = models.DateField(verbose_name="Fecha de Salida")
    hora_salida = models.TimeField(verbose_name="Hora de Salida")
    fecha_vuelta = models.DateField(
        null=True, blank=True,
        verbose_name="Fecha de Vuelta",
        help_text="Solo aplica para viajes de Ida y Vuelta."
    )
    hora_vuelta = models.TimeField(
        null=True, blank=True,
        verbose_name="Hora de Vuelta",
        help_text="Solo aplica para viajes de Ida y Vuelta."
    )
    precio_usd = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio (USD)")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    fecha_inicio_venta = models.DateField(
        null=True, blank=True,
        verbose_name="Inicio de Venta",
        help_text="Desde cuándo se pueden reservar puestos. Vacío = ya disponible."
    )
    fecha_fin_venta = models.DateField(
        null=True, blank=True,
        verbose_name="Expiración de Compra",
        help_text="Fecha límite para comprar puestos. Vacío = abierto hasta la salida."
    )

    class Meta:
        verbose_name = "Viaje"
        verbose_name_plural = "Viajes"
        ordering = ['fecha_salida', 'hora_salida']

    def __str__(self):
        tipo = "↔" if self.tipo_viaje == 'ida_vuelta' else "→"
        return f"{self.ruta.origen} {tipo} {self.ruta.destino} - {self.fecha_salida} {self.hora_salida}"


class RutaAerorutasSnapshot(models.Model):
    """
    Catálogo de viajes de Aerorutas precargado por fecha.
    Lo llena el comando `precargar_rutas` (barre todos los pares de oficinas) y
    lo sirve el endpoint /aerorutas/viajes/ al instante (sin barrer en vivo).
    """
    fecha = models.DateField(unique=True, db_index=True, verbose_name="Fecha")
    data = models.JSONField(
        default=list, blank=True,
        verbose_name="Viajes (JSON)",
        help_text="Lista de viajes ya transformados al formato de la app."
    )
    actualizado = models.DateTimeField(auto_now=True, verbose_name="Última precarga")

    class Meta:
        verbose_name = "Catálogo Aerorutas (por fecha)"
        verbose_name_plural = "Catálogo Aerorutas (por fecha)"
        ordering = ['fecha']

    def __str__(self):
        n = len(self.data) if isinstance(self.data, list) else 0
        return f"{self.fecha} — {n} viajes"


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
    rif = models.CharField(max_length=20, blank=True, default='', verbose_name="RIF")
    domicilio_fiscal = models.TextField(blank=True, default='', verbose_name="Domicilio Fiscal")
    banco = models.CharField(max_length=100, blank=True, default='', verbose_name="Banco")
    cuenta_bancaria = models.CharField(max_length=30, blank=True, default='', verbose_name="Cuenta Bancaria")
    tipo_cuenta = models.CharField(max_length=30, blank=True, default='', verbose_name="Tipo de Cuenta")
    telefono_contacto = models.CharField(max_length=20, blank=True, default='', verbose_name="Teléfono de Contacto")
    lema = models.CharField(max_length=200, blank=True, default='', verbose_name="Lema de la Empresa")
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
