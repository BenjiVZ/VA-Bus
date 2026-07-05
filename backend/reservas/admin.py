from django.contrib import admin
from .models import Reserva


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'codigo_ticket', 'usuario', 'viaje', 'numero_asiento', 'piso_asiento',
        'estado', 'nombre_pasajero', 'cedula_pasajero',
        'es_menor_edad', 'viaja_con_animal', 'es_discapacitado', 'fecha_creacion'
    )
    list_filter = ('estado', 'es_menor_edad', 'viaja_con_animal', 'es_discapacitado', 'viaje__fecha_salida', 'viaje__ruta')
    list_editable = ('estado',)
    search_fields = (
        'codigo_ticket', 'grupo_pago',
        'usuario__username', 'usuario__first_name', 'usuario__last_name',
        'nombre_pasajero', 'cedula_pasajero',
        'viaje__ruta__origen', 'viaje__ruta__destino'
    )
    date_hierarchy = 'fecha_creacion'
    readonly_fields = ('codigo_ticket', 'grupo_pago', 'fecha_creacion', 'fecha_actualizacion')

    fieldsets = (
        ('Información del Viaje', {
            'fields': ('viaje', 'numero_asiento', 'piso_asiento')
        }),
        ('Pasajero', {
            'fields': ('usuario', 'nombre_pasajero', 'cedula_pasajero',
                       'es_menor_edad', 'menor_no_es_hijo', 'viaja_con_animal', 'tipo_mascota', 'es_discapacitado',
                       'para_otra_persona', 'nombre_asignado', 'cedula_asignado')
        }),
        ('Documentos de Menor de Edad', {
            'fields': ('doc_partida_nacimiento', 'doc_foto_menor', 'doc_cedula_representante', 'doc_permiso_viaje'),
            'classes': ('collapse',),
            'description': 'Documentos subidos cuando el pasajero es menor de edad. '
                           'El permiso de viaje es obligatorio si el menor no es hijo del comprador.'
        }),
        ('Documentos de Mascota', {
            'fields': ('doc_vacunacion_animal',),
            'classes': ('collapse',),
            'description': 'Tarjeta de vacunación del animal.'
        }),
        ('Documento de Discapacidad', {
            'fields': ('doc_discapacidad',),
            'classes': ('collapse',),
            'description': 'Certificado médico, RCP o documento que acredite la discapacidad.'
        }),
        ('Estado y Ticket', {
            'fields': ('estado', 'codigo_ticket', 'grupo_pago'),
            'description': 'El código de ticket se genera solo al confirmar la reserva.'
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
