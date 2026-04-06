from django import forms
from django.contrib import admin
from django.utils import timezone
from .models import Ruta, Autobus, PisoAutobus, Viaje, ConfiguracionGeneral
from .services import actualizar_tasa_bcv


class PisoAutobusForm(forms.ModelForm):
    class Meta:
        model = PisoAutobus
        fields = '__all__'
        widgets = {
            'layout': forms.Textarea(attrs={
                'rows': 3,
                'style': 'width: 100%; font-family: monospace; font-size: 11px;'
            }),
        }


class PisoAutobusInline(admin.StackedInline):
    model = PisoAutobus
    form = PisoAutobusForm
    extra = 0
    min_num = 1
    fields = ('numero_piso', 'filas', 'columnas', 'layout')

    class Media:
        css = {'all': ('admin/css/seat_editor.css',)}
        js = ('admin/js/seat_editor.js',)


@admin.register(Ruta)
class RutaAdmin(admin.ModelAdmin):
    list_display = ('origen', 'destino', 'duracion_estimada')
    search_fields = ('origen', 'destino')


@admin.register(Autobus)
class AutobusAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'placa', 'marca', 'color', 'anio', 'pisos', 'capacidad_total')
    search_fields = ('nombre', 'placa', 'marca')
    inlines = [PisoAutobusInline]


@admin.register(Viaje)
class ViajeAdmin(admin.ModelAdmin):
    list_display = (
        'ruta', 'autobus', 'tipo_viaje', 'fecha_salida', 'hora_salida',
        'fecha_vuelta', 'precio_usd', 'fecha_fin_venta', 'activo'
    )
    list_filter = ('activo', 'tipo_viaje', 'fecha_salida', 'ruta')
    search_fields = ('ruta__origen', 'ruta__destino')
    date_hierarchy = 'fecha_salida'
    fieldsets = (
        ('Ruta y Autobús', {
            'fields': ('ruta', 'autobus')
        }),
        ('Viaje de Ida', {
            'fields': ('tipo_viaje', 'fecha_salida', 'hora_salida')
        }),
        ('Viaje de Vuelta', {
            'fields': ('fecha_vuelta', 'hora_vuelta'),
            'classes': ('collapse',),
            'description': 'Solo aplica si el tipo de viaje es "Ida y Vuelta".'
        }),
        ('Precio y Disponibilidad', {
            'fields': ('precio_usd', 'activo')
        }),
        ('Ventana de Compra', {
            'fields': ('fecha_inicio_venta', 'fecha_fin_venta'),
            'description': 'Cuándo se abren y cuándo expiran las reservas. Dejar vacío = siempre disponible.'
        }),
    )

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['portal_url'] = '/admin/portal-viajes/'
        return super().changelist_view(request, extra_context)

    class Media:
        js = ('admin/js/viaje_tipo.js',)


@admin.register(ConfiguracionGeneral)
class ConfiguracionGeneralAdmin(admin.ModelAdmin):
    list_display = ('nombre_empresa', 'rif', 'whatsapp_vendedor', 'tasa_bcv', 'tasa_actualizada')

    def has_add_permission(self, request):
        return not ConfiguracionGeneral.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        obj = ConfiguracionGeneral.load()
        from django.shortcuts import redirect
        return redirect(f'/admin/viajes/configuraciongeneral/{obj.pk}/change/')

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_save_and_add_another'] = False
        extra_context['show_delete_link'] = False

        if request.method == 'POST' and '_actualizar_tasa' in request.POST:
            exito, mensaje = actualizar_tasa_bcv()
            from django.contrib import messages
            if exito:
                messages.success(request, mensaje)
            else:
                messages.error(request, mensaje)
            from django.shortcuts import redirect
            return redirect(f'/admin/viajes/configuraciongeneral/{object_id}/change/')

        return super().change_view(request, object_id, form_url, extra_context)

    class Media:
        js = ('admin/js/tasa_button.js',)
