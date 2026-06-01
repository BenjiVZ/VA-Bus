from django.urls import path
from .views import (
    RutaListView, OficinaListView, ViajeListView, ViajeDetailView,
    ViajeAsientosView, TasaCambioView, ConfiguracionPublicaView,
    StatsPublicView
)

urlpatterns = [
    path('rutas/', RutaListView.as_view(), name='rutas-list'),
    path('oficinas/', OficinaListView.as_view(), name='oficinas-list'),
    path('viajes/', ViajeListView.as_view(), name='viajes-list'),
    path('viajes/<int:pk>/', ViajeDetailView.as_view(), name='viaje-detail'),
    path('viajes/<int:pk>/asientos/', ViajeAsientosView.as_view(), name='viaje-asientos'),
    path('tasa-cambio/', TasaCambioView.as_view(), name='tasa-cambio'),
    path('configuracion/', ConfiguracionPublicaView.as_view(), name='configuracion'),
    path('stats/', StatsPublicView.as_view(), name='stats-public'),
]

