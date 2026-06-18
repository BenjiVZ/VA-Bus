import logging
from decimal import Decimal

from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from reservas.models import Reserva
from viajes.models import ConfiguracionGeneral

from . import services
from .bancos import BANCOS
from .operaciones import aplicar_respuesta
from .models import OperacionDebitoOTP
from .serializers import GenerarOtpSerializer, ConfirmarDebitoSerializer


def _grupo_ya_pagado(grupo_pago) -> bool:
    """True si el grupo ya tiene un pago aprobado (R4 aceptada o reserva confirmada).

    Protege contra pagos duplicados: una vez pagado, ningún otro cobro debe pasar,
    venga de otra operación R4 o de un comprobante manual ya validado.
    """
    if OperacionDebitoOTP.objects.filter(grupo_pago=grupo_pago, estado='aceptada').exists():
        return True
    return Reserva.objects.filter(grupo_pago=grupo_pago, estado='confirmado').exists()


class BancosListView(APIView):
    """Lista pública de códigos de banco (fuente única para web y móvil)."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(BANCOS)

logger = logging.getLogger('r4conecta')


class GenerarOtpView(APIView):
    """Paso 1: solicita al banco un OTP para cobrar la reserva por débito inmediato."""
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'r4_otp'

    def post(self, request):
        ser = GenerarOtpSerializer(data=request.data)
        if not ser.is_valid():
            return Response({'error': 'Datos inválidos.', 'detalles': ser.errors},
                            status=status.HTTP_400_BAD_REQUEST)
        d = ser.validated_data
        grupo_pago = d['grupo_pago']

        # Si el grupo ya fue pagado, no iniciar otro cobro (evita duplicados).
        if _grupo_ya_pagado(grupo_pago):
            return Response({'error': 'Este pago ya fue aprobado.'},
                            status=status.HTTP_409_CONFLICT)

        reservas = Reserva.objects.filter(
            grupo_pago=grupo_pago, usuario=request.user,
            estado__in=['pendiente', 'apartado'],
        ).select_related('viaje')
        if not reservas.exists():
            return Response({'error': 'No hay reservas por pagar para este grupo de pago.'},
                            status=status.HTTP_404_NOT_FOUND)

        # ── Monto calculado en el servidor: Σ(precio_usd) × tasa BCV (en Bs) ──
        config = ConfiguracionGeneral.load()
        tasa = config.tasa_bcv if config else None
        if not tasa or tasa <= 0:
            return Response({'error': 'Tasa BCV no disponible. Intenta más tarde.'},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
        monto_usd = sum((r.viaje.precio_usd for r in reservas), Decimal('0'))
        monto_str = services._fmt_monto(monto_usd * tasa)

        nombre = (d.get('nombre') or request.user.get_full_name()
                  or request.user.username)[:40]
        concepto = (d.get('concepto') or f'Pasaje {grupo_pago.hex[:8]}')[:30]

        op = OperacionDebitoOTP.objects.create(
            usuario=request.user, grupo_pago=grupo_pago,
            banco=d['banco'], cedula=d['cedula'], telefono=d['telefono'],
            nombre=nombre, monto=Decimal(monto_str), concepto=concepto,
            estado='otp_generado',
        )

        try:
            resp = services.generar_otp(d['banco'], monto_str, d['telefono'], d['cedula'])
        except services.R4Error as e:
            op.estado = 'error'
            op.mensaje = e.message[:255]
            op.save(update_fields=['estado', 'mensaje', 'actualizado'])
            return Response({'error': e.message}, status=status.HTTP_502_BAD_GATEWAY)

        op.otp_response = resp
        op.code = str(resp.get('code', ''))[:10]
        op.mensaje = str(resp.get('message', ''))[:255]
        op.save(update_fields=['otp_response', 'code', 'mensaje', 'actualizado'])

        otp_enviado = op.code == '202' or resp.get('success') is True
        return Response({
            'operacion_id': op.pk,
            'code': op.code,
            'message': op.mensaje,
            'monto': monto_str,
            'otp_enviado': otp_enviado,
        }, status=status.HTTP_200_OK if otp_enviado else status.HTTP_400_BAD_REQUEST)


class ConfirmarDebitoView(APIView):
    """Paso 2: completa el débito con el OTP. Acepta un comprobante opcional."""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        ser = ConfirmarDebitoSerializer(data=request.data)
        if not ser.is_valid():
            return Response({'error': 'Datos inválidos.', 'detalles': ser.errors},
                            status=status.HTTP_400_BAD_REQUEST)
        d = ser.validated_data

        try:
            op = OperacionDebitoOTP.objects.get(pk=d['operacion_id'], usuario=request.user)
        except OperacionDebitoOTP.DoesNotExist:
            return Response({'error': 'Operación no encontrada.'},
                            status=status.HTTP_404_NOT_FOUND)
        if op.estado == 'aceptada':
            return Response({'error': 'Esta operación ya fue aprobada.'},
                            status=status.HTTP_409_CONFLICT)
        # Que no se cobre dos veces el mismo grupo (otra operación ya aprobada,
        # o reservas ya confirmadas por otro método de pago).
        if _grupo_ya_pagado(op.grupo_pago):
            return Response({'error': 'Este pago ya fue aprobado.'},
                            status=status.HTTP_409_CONFLICT)

        # Comprobante opcional adjunto por el cliente.
        comprobante = request.FILES.get('comprobante')
        if comprobante:
            op.comprobante = comprobante
            op.save(update_fields=['comprobante', 'actualizado'])

        try:
            resp = services.debito_inmediato(
                op.banco, op.monto, op.telefono, op.cedula,
                op.nombre, d['otp'], op.concepto,
            )
        except services.R4Error as e:
            op.estado = 'error'
            op.mensaje = e.message[:255]
            op.save(update_fields=['estado', 'mensaje', 'actualizado'])
            return Response({'error': e.message}, status=status.HTTP_502_BAD_GATEWAY)

        return _resolver_respuesta(op, resp, campo='debito_response')


class ConsultarOperacionView(APIView):
    """Resuelve operaciones que quedaron en espera (AC00) consultando al banco."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            op = OperacionDebitoOTP.objects.get(pk=pk, usuario=request.user)
        except OperacionDebitoOTP.DoesNotExist:
            return Response({'error': 'Operación no encontrada.'},
                            status=status.HTTP_404_NOT_FOUND)
        if op.estado == 'aceptada':
            return Response({'estado': 'aceptada', 'code': op.code, 'referencia': op.referencia})
        if op.estado != 'en_espera' or not op.operacion_id:
            return Response({'error': 'La operación no está en espera de confirmación.'},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            resp = services.consultar_operacion(op.operacion_id)
        except services.R4Error as e:
            return Response({'error': e.message}, status=status.HTTP_502_BAD_GATEWAY)

        return _resolver_respuesta(op, resp, campo='consulta_response')


class OperacionDetalleView(APIView):
    """Estado de una operación (para polling del frontend)."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            op = OperacionDebitoOTP.objects.get(pk=pk, usuario=request.user)
        except OperacionDebitoOTP.DoesNotExist:
            return Response({'error': 'Operación no encontrada.'},
                            status=status.HTTP_404_NOT_FOUND)
        return Response({
            'operacion_id': op.pk,
            'estado': op.estado,
            'code': op.code,
            'message': op.mensaje,
            'referencia': op.referencia,
            'monto': str(op.monto),
            'grupo_pago': str(op.grupo_pago) if op.grupo_pago else None,
        })


def _resolver_respuesta(op, resp, campo):
    """Aplica la respuesta del banco y construye la Response HTTP al cliente."""
    estado = aplicar_respuesta(op, resp, campo=campo)
    http = status.HTTP_202_ACCEPTED if estado == 'en_espera' else status.HTTP_200_OK
    return Response({
        'estado': estado,
        'code': op.code,
        'operacion_id': op.pk,
        'referencia': op.referencia,
        'message': op.mensaje,
    }, status=http)
