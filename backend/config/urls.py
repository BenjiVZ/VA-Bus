"""Aerorutas URL Configuration"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from viajes.views import portal_viajes_view, eliminar_viaje_view

admin.site.site_header = "Aerorutas de Venezuela — Administración"
admin.site.site_title = "Aerorutas Admin"
admin.site.index_title = "Panel de Administración"

urlpatterns = [
    path('admin/portal-viajes/', portal_viajes_view, name='portal-viajes'),
    path('admin/portal-viajes/eliminar/<int:viaje_id>/', eliminar_viaje_view, name='eliminar-viaje'),
    path('admin/', admin.site.urls),
    path('api/', include('viajes.urls')),
    path('api/', include('reservas.urls')),
    path('api/', include('pagos.urls')),
    path('api/auth/', include('usuarios.urls')),
    path('api/externo/', include('api_externa.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

