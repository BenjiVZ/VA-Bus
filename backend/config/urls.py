"""Aerorutas URL Configuration"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

admin.site.site_header = "Aerorutas de Venezuela — Administración"
admin.site.site_title = "Aerorutas Admin"
admin.site.index_title = "Panel de Administración"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('viajes.urls')),
    path('api/', include('reservas.urls')),
    path('api/', include('pagos.urls')),
    path('api/auth/', include('usuarios.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

