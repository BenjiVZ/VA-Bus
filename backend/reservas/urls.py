from django.urls import path
from .views import (
    CrearReservaView, MisReservasView,
    AdminReservasViajeView, AdminCambiarEstadoView,
    AdminCambiarAsientoView, AdminViajesListView,
    AdminBusesListView,
)

urlpatterns = [
    path('reservas/', CrearReservaView.as_view(), name='crear-reserva'),
    path('mis-reservas/', MisReservasView.as_view(), name='mis-reservas'),

    # Admin endpoints
    path('admin/viajes/', AdminViajesListView.as_view(), name='admin-viajes'),
    path('admin/viajes/<int:viaje_id>/reservas/', AdminReservasViajeView.as_view(), name='admin-reservas-viaje'),
    path('admin/reservas/<int:reserva_id>/estado/', AdminCambiarEstadoView.as_view(), name='admin-cambiar-estado'),
    path('admin/reservas/<int:reserva_id>/asiento/', AdminCambiarAsientoView.as_view(), name='admin-cambiar-asiento'),
    path('admin/buses/', AdminBusesListView.as_view(), name='admin-buses'),
]
