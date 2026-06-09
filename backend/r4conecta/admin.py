from django.contrib import admin

from . import services
from .models import OperacionDebitoOTP
from .operaciones import aplicar_respuesta


@admin.register(OperacionDebitoOTP)
class OperacionDebitoOTPAdmin(admin.ModelAdmin):
    """Página de movimientos de Débito Inmediato (OTP)."""
    list_display = ('id', 'estado', 'code', 'cliente', 'cedula', 'telefono',
                    'monto', 'referencia', 'operacion_id', 'creado')
    list_filter = ('estado', 'creado')
    search_fields = ('cedula', 'telefono', 'nombre', 'referencia',
                     'operacion_id', 'grupo_pago', 'usuario__username')
    date_hierarchy = 'creado'
    ordering = ('-creado',)
    actions = ['validar_en_banco']
    readonly_fields = (
        'usuario', 'grupo_pago', 'banco', 'cedula', 'telefono', 'nombre',
        'monto', 'concepto', 'comprobante', 'estado', 'code', 'mensaje',
        'referencia', 'operacion_id', 'otp_response', 'debito_response',
        'consulta_response', 'creado', 'actualizado',
    )

    def cliente(self, obj):
        return obj.nombre or (obj.usuario.get_full_name() if obj.usuario else '—')
    cliente.short_description = 'Cliente'

    def has_add_permission(self, request):
        return False

    @admin.action(description='Validar en el banco (ConsultarOperaciones)')
    def validar_en_banco(self, request, queryset):
        """Consulta manualmente al banco las operaciones en espera seleccionadas."""
        ok = espera = err = 0
        for op in queryset.filter(estado='en_espera').exclude(operacion_id=''):
            try:
                resp = services.consultar_operacion(op.operacion_id)
            except services.R4Error as e:
                err += 1
                self.message_user(request, f'Op {op.pk}: {e}', level='error')
                continue
            estado = aplicar_respuesta(op, resp, campo='consulta_response')
            if estado == 'aceptada':
                ok += 1
            elif estado == 'en_espera':
                espera += 1
            else:
                err += 1
        self.message_user(
            request,
            f'Validadas — aprobadas: {ok}, aún en espera: {espera}, rechazadas/error: {err}')
