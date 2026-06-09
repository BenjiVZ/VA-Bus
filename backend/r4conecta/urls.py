from django.urls import path
from .views import (
    BancosListView,
    GenerarOtpView,
    ConfirmarDebitoView,
    ConsultarOperacionView,
    OperacionDetalleView,
)
from .test_views import test_page, TestGenerarOtp, TestDebito, TestConsultar

urlpatterns = [
    path('bancos/', BancosListView.as_view(), name='r4-bancos'),
    path('debito/generar-otp/', GenerarOtpView.as_view(), name='r4-generar-otp'),
    path('debito/confirmar/', ConfirmarDebitoView.as_view(), name='r4-confirmar-debito'),
    path('debito/<int:pk>/consultar/', ConsultarOperacionView.as_view(), name='r4-consultar-operacion'),
    path('debito/<int:pk>/', OperacionDetalleView.as_view(), name='r4-operacion-detalle'),

    # ── Página de prueba (solo DEBUG) ──
    path('test/', test_page, name='r4-test-page'),
    path('test/generar-otp/', TestGenerarOtp.as_view(), name='r4-test-generar-otp'),
    path('test/debito/', TestDebito.as_view(), name='r4-test-debito'),
    path('test/consultar/', TestConsultar.as_view(), name='r4-test-consultar'),
]
