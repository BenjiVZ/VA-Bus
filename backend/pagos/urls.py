from django.urls import path
from .views import (
    MetodosPagoListView,
    CrearComprobanteView,
    EstadoComprobanteView,
    AdminComprobantesListView,
    AdminValidarComprobanteView,
)

urlpatterns = [
    path('metodos-pago/', MetodosPagoListView.as_view(), name='metodos-pago'),
    path('comprobantes/', CrearComprobanteView.as_view(), name='crear-comprobante'),
    path('comprobantes/<uuid:grupo_pago>/', EstadoComprobanteView.as_view(), name='estado-comprobante'),
    path('admin/comprobantes/', AdminComprobantesListView.as_view(), name='admin-comprobantes'),
    path('admin/comprobantes/<uuid:comprobante_id>/validar/', AdminValidarComprobanteView.as_view(), name='admin-validar-comprobante'),
]
