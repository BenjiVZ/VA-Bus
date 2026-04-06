from django.urls import path
from .views import (
    ViajesListView, ViajeDetalleView,
    AsientosViajeView, PasajerosViajeView,
    OcuparAsientosView,
)

urlpatterns = [
    path('viajes/', ViajesListView.as_view(), name='externo_viajes'),
    path('viajes/<int:viaje_id>/', ViajeDetalleView.as_view(), name='externo_viaje_detalle'),
    path('viajes/<int:viaje_id>/asientos/', AsientosViajeView.as_view(), name='externo_asientos'),
    path('viajes/<int:viaje_id>/pasajeros/', PasajerosViajeView.as_view(), name='externo_pasajeros'),
    path('viajes/<int:viaje_id>/ocupar-asientos/', OcuparAsientosView.as_view(), name='externo_ocupar'),
]
