from django.urls import path
from .views import (
    CrearReservaView, MisReservasView,
    BloquearAsientoView, LiberarAsientoView,
    SubirDocumentosMenorView, SubirDocVacunacionView, SubirDocDiscapacidadView,
    AdminReservasViajeView, AdminCambiarEstadoView,
    AdminCambiarAsientoView, AdminViajesListView,
    AdminBusesListView,
    TicketView, VerificarTicketView,
)

urlpatterns = [
    path('reservas/', CrearReservaView.as_view(), name='crear-reserva'),
    path('reservas/bloquear-asiento/', BloquearAsientoView.as_view(), name='bloquear-asiento'),
    path('reservas/liberar-asiento/', LiberarAsientoView.as_view(), name='liberar-asiento'),
    path('mis-reservas/', MisReservasView.as_view(), name='mis-reservas'),
    path('reservas/<int:reserva_id>/documentos-menor/', SubirDocumentosMenorView.as_view(), name='subir-documentos-menor'),
    path('reservas/<int:reserva_id>/doc-vacunacion/', SubirDocVacunacionView.as_view(), name='subir-doc-vacunacion'),
    path('reservas/<int:reserva_id>/doc-discapacidad/', SubirDocDiscapacidadView.as_view(), name='subir-doc-discapacidad'),

    # Tickets
    path('ticket/<uuid:grupo_pago>/', TicketView.as_view(), name='ticket'),
    path('verificar/<str:codigo_ticket>/', VerificarTicketView.as_view(), name='verificar-ticket'),

    # Admin endpoints
    path('admin/viajes/', AdminViajesListView.as_view(), name='admin-viajes'),
    path('admin/viajes/<int:viaje_id>/reservas/', AdminReservasViajeView.as_view(), name='admin-reservas-viaje'),
    path('admin/reservas/<int:reserva_id>/estado/', AdminCambiarEstadoView.as_view(), name='admin-cambiar-estado'),
    path('admin/reservas/<int:reserva_id>/asiento/', AdminCambiarAsientoView.as_view(), name='admin-cambiar-asiento'),
    path('admin/buses/', AdminBusesListView.as_view(), name='admin-buses'),
]
