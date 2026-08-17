"""Rutas del back office. Todo cuelga de /panel/."""
from django.urls import path

from pagos.caja_views import caja_view
from r4conecta.panel_views import panel_pagos
from viajes.views import eliminar_viaje_view, portal_viajes_view

from . import views

app_name = 'backoffice'

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('ingresar/', views.ingresar, name='ingresar'),
    path('salir/', views.salir, name='salir'),

    path('caja/', caja_view, name='caja'),

    path('viajes/', portal_viajes_view, name='viajes'),
    path('viajes/eliminar/<int:viaje_id>/', eliminar_viaje_view, name='eliminar_viaje'),
    path('rutas/', views.rutas, name='rutas'),

    path('boletos/', views.boletos, name='boletos'),
    path('comprobantes/', views.comprobantes, name='comprobantes'),
    path('arqueo/', views.arqueo, name='arqueo'),
    path('pagos-r4/', panel_pagos, name='pagos_r4'),
]
