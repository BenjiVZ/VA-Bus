from django.contrib import admin
from .models import Reserva


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'usuario', 'viaje', 'numero_asiento', 'piso_asiento',
        'estado', 'nombre_pasajero', 'cedula_pasajero',
        'es_menor_edad', 'viaja_con_animal', 'es_discapacitado', 'fecha_creacion'
    )
    list_filter = ('estado', 'es_menor_edad', 'viaja_con_animal', 'es_discapacitado', 'viaje__fecha_salida', 'viaje__ruta')
    list_editable = ('estado',)
    search_fields = (
        'usuario__username', 'usuario__first_name', 'usuario__last_name',
        'nombre_pasajero', 'cedula_pasajero',
        'viaje__ruta__origen', 'viaje__ruta__destino'
    )
    date_hierarchy = 'fecha_creacion'
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')

    fieldsets = (
        ('Información del Viaje', {
            'fields': ('viaje', 'numero_asiento', 'piso_asiento')
        }),
        ('Pasajero', {
            'fields': ('usuario', 'nombre_pasajero', 'cedula_pasajero',
                       'es_menor_edad', 'viaja_con_animal', 'es_discapacitado',
                       'para_otra_persona', 'nombre_asignado', 'cedula_asignado')
        }),
        ('Estado', {
            'fields': ('estado',)
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
