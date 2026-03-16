from django.contrib import admin
from .models import MetodoPago, DatoMetodoPago, ComprobantePago


class DatoMetodoPagoInline(admin.TabularInline):
    model = DatoMetodoPago
    extra = 1
    fields = ('etiqueta', 'valor', 'orden')
    ordering = ('orden',)


@admin.register(MetodoPago)
class MetodoPagoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'moneda', 'descripcion', 'activo', 'orden')
    list_editable = ('activo', 'orden')
    list_filter = ('activo', 'moneda')
    inlines = [DatoMetodoPagoInline]
    ordering = ('orden',)


@admin.register(ComprobantePago)
class ComprobantePagoAdmin(admin.ModelAdmin):
    list_display = (
        'id_corto', 'usuario', 'metodo_pago', 'monto', 'moneda',
        'estado', 'numero_referencia', 'fecha_creacion'
    )
    list_filter = ('estado', 'moneda', 'metodo_pago', 'fecha_creacion')
    search_fields = (
        'usuario__username', 'usuario__first_name',
        'numero_referencia', 'grupo_pago'
    )
    readonly_fields = (
        'id', 'grupo_pago', 'usuario', 'metodo_pago',
        'numero_referencia', 'imagen', 'monto', 'moneda',
        'fecha_creacion', 'fecha_revision'
    )
    list_editable = ('estado',)
    date_hierarchy = 'fecha_creacion'

    fieldsets = (
        ('Comprobante', {
            'fields': ('id', 'grupo_pago', 'usuario', 'metodo_pago', 'imagen')
        }),
        ('Datos del Pago', {
            'fields': ('monto', 'moneda', 'numero_referencia')
        }),
        ('Validación', {
            'fields': ('estado', 'revisado_por', 'nota_admin', 'fecha_revision')
        }),
        ('Fechas', {
            'fields': ('fecha_creacion',),
            'classes': ('collapse',)
        }),
    )

    def id_corto(self, obj):
        return str(obj.id)[:8]
    id_corto.short_description = "ID"
