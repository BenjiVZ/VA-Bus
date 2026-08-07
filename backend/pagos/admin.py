from django.contrib import admin
from .models import MetodoPago, DatoMetodoPago, ComprobantePago, PagoCaja


class DatoMetodoPagoInline(admin.TabularInline):
    model = DatoMetodoPago
    extra = 1
    fields = ('etiqueta', 'valor', 'orden')
    ordering = ('orden',)


@admin.register(MetodoPago)
class MetodoPagoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'tipo', 'moneda', 'descripcion', 'requiere_foto_billete',
                    'disponible_web', 'disponible_caja', 'activo', 'orden')
    list_editable = ('activo', 'orden', 'requiere_foto_billete',
                     'disponible_web', 'disponible_caja')
    list_filter = ('activo', 'moneda', 'tipo', 'requiere_foto_billete',
                   'disponible_web', 'disponible_caja')
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
        'numero_referencia', 'imagen', 'foto_billete', 'monto', 'moneda',
        'fecha_creacion', 'fecha_revision'
    )
    list_editable = ('estado',)
    date_hierarchy = 'fecha_creacion'

    fieldsets = (
        ('Comprobante', {
            'fields': ('id', 'grupo_pago', 'usuario', 'metodo_pago', 'imagen', 'foto_billete')
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


@admin.register(PagoCaja)
class PagoCajaAdmin(admin.ModelAdmin):
    """Arqueo de taquilla. Solo lectura: el registro lo crea el módulo de Caja."""
    list_display = ('fecha_creacion', 'cliente_nombre', 'monto_mostrado', 'monto_usd',
                    'metodo_pago', 'cajero', 'referencia')
    list_filter = ('moneda', 'metodo_pago', 'cajero', 'fecha_creacion')
    search_fields = ('cliente_nombre', 'cliente_cedula', 'referencia', 'grupo_pago')
    date_hierarchy = 'fecha_creacion'
    ordering = ('-fecha_creacion',)

    def has_add_permission(self, request):
        return False  # se registra desde /admin/caja/

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    @admin.display(description='Cobrado', ordering='monto')
    def monto_mostrado(self, obj):
        return f"{'Bs.' if obj.moneda == 'BS' else '$'} {obj.monto}"
