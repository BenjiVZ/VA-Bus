from django.urls import path
from .views import (
    RutaListView, OficinaListView, ViajeListView, ViajeDetailView,
    ViajeAsientosView, TasaCambioView, ConfiguracionPublicaView,
    StatsPublicView,
    AerorutasOficinasView, AerorutasRutasView, AerorutasPuestosView,
    AerorutasApartarView, AerorutasViajesView, AerorutasViajeAsientosView,
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

    # ── Integración Aerorutas (consulta en vivo) ──
    path('aerorutas/oficinas/', AerorutasOficinasView.as_view(), name='aerorutas-oficinas'),
    path('aerorutas/rutas/', AerorutasRutasView.as_view(), name='aerorutas-rutas'),
    path('aerorutas/puestos/', AerorutasPuestosView.as_view(), name='aerorutas-puestos'),
    path('aerorutas/apartar/', AerorutasApartarView.as_view(), name='aerorutas-apartar'),
    # Mismo formato que /viajes/ y /viajes/<id>/asientos/ (para reusar la UI)
    path('aerorutas/viajes/', AerorutasViajesView.as_view(), name='aerorutas-viajes'),
    path('aerorutas/viajes/<str:trip_id>/asientos/', AerorutasViajeAsientosView.as_view(), name='aerorutas-viaje-asientos'),
]

