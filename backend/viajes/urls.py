from django.urls import path
from .views import (
    RutaListView, ViajeListView, ViajeDetailView,
    ViajeAsientosView, TasaCambioView, ConfiguracionPublicaView
)

urlpatterns = [
    path('rutas/', RutaListView.as_view(), name='rutas-list'),
    path('viajes/', ViajeListView.as_view(), name='viajes-list'),
    path('viajes/<int:pk>/', ViajeDetailView.as_view(), name='viaje-detail'),
    path('viajes/<int:pk>/asientos/', ViajeAsientosView.as_view(), name='viaje-asientos'),
    path('tasa-cambio/', TasaCambioView.as_view(), name='tasa-cambio'),
    path('configuracion/', ConfiguracionPublicaView.as_view(), name='configuracion'),
]
