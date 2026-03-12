"""Aerorutas URL Configuration"""

from django.contrib import admin
from django.urls import path, include

admin.site.site_header = "Aerorutas de Venezuela — Administración"
admin.site.site_title = "Aerorutas Admin"
admin.site.index_title = "Panel de Administración"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('viajes.urls')),
    path('api/', include('reservas.urls')),
    path('api/auth/', include('usuarios.urls')),
]
