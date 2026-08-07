from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser

from .models import MetodoPago, ComprobantePago
from .services import validar_comprobante
from .serializers import (
    MetodoPagoSerializer, ComprobantePagoSerializer,
    CrearComprobanteSerializer, AdminComprobanteSerializer,
)
from reservas.models import Reserva


class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff


# ═══════════════════════════════════════════════
# ── PUBLIC / AUTH ENDPOINTS ──
# ═══════════════════════════════════════════════

class MetodosPagoListView(APIView):
    """Lista métodos de pago activos con sus datos bancarios."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # Solo los del canal WEB: los de taquilla (efectivo, débito, Cashea…)
        # no se le ofrecen al cliente que paga desde la web o la app.
        metodos = (MetodoPago.objects
                   .filter(activo=True, disponible_web=True)
                   .prefetch_related('datos'))
        return Response(MetodoPagoSerializer(metodos, many=True).data)


class CrearComprobanteView(APIView):
    """Cliente sube comprobante de pago."""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = CrearComprobanteSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Datos inválidos.", "detalles": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        grupo_pago = serializer.validated_data['grupo_pago']
        metodo_pago_id = serializer.validated_data['metodo_pago_id']

        # Verify the reservations belong to this user
        reservas = Reserva.objects.filter(
            grupo_pago=grupo_pago, usuario=request.user
        )
        if not reservas.exists():
            return Response(
                {"error": "No se encontraron reservas para este grupo de pago."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if a comprobante already exists for this group
        if ComprobantePago.objects.filter(grupo_pago=grupo_pago).exists():
            return Response(
                {"error": "Ya se envió un comprobante para esta orden."},
                status=status.HTTP_409_CONFLICT
            )

        # Verify metodo_pago exists (y que sea del canal web: un cliente no
        # puede reportar un pago con un método que solo existe en taquilla).
        try:
            metodo = MetodoPago.objects.get(
                pk=metodo_pago_id, activo=True, disponible_web=True)
        except MetodoPago.DoesNotExist:
            return Response(
                {"error": "Método de pago no válido."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate foto_billete when required
        foto_billete = serializer.validated_data.get('foto_billete')
        if metodo.requiere_foto_billete and not foto_billete:
            return Response(
                {"error": "Este método de pago requiere que subas una foto del billete."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create comprobante
        comprobante = ComprobantePago.objects.create(
            grupo_pago=grupo_pago,
            usuario=request.user,
            metodo_pago=metodo,
            numero_referencia=serializer.validated_data.get('numero_referencia', ''),
            imagen=serializer.validated_data['imagen'],
            foto_billete=foto_billete,
            monto=serializer.validated_data['monto'],
            moneda=serializer.validated_data.get('moneda', 'BS'),
        )

        # Move all reservations from 'pendiente' to 'apartado'
        reservas.filter(estado='pendiente').update(estado='apartado')

        return Response({
            "mensaje": "Comprobante enviado exitosamente. Tu puesto está apartado hasta que el admin valide el pago.",
            "comprobante": ComprobantePagoSerializer(comprobante).data,
        }, status=status.HTTP_201_CREATED)


class EstadoComprobanteView(APIView):
    """Consultar el estado de un comprobante por grupo_pago."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, grupo_pago):
        try:
            comprobante = ComprobantePago.objects.get(
                grupo_pago=grupo_pago, usuario=request.user
            )
        except ComprobantePago.DoesNotExist:
            return Response(
                {"existe": False, "mensaje": "No se ha enviado comprobante aún."},
                status=status.HTTP_200_OK
            )

        return Response({
            "existe": True,
            "comprobante": ComprobantePagoSerializer(comprobante).data,
        })


# ═══════════════════════════════════════════════
# ── ADMIN ENDPOINTS ──
# ═══════════════════════════════════════════════

class AdminComprobantesListView(APIView):
    """Lista todos los comprobantes para validación."""
    permission_classes = [IsAdminUser]

    def get(self, request):
        estado_filter = request.query_params.get('estado', None)
        qs = ComprobantePago.objects.select_related(
            'usuario', 'metodo_pago'
        ).all()

        if estado_filter:
            qs = qs.filter(estado=estado_filter)

        data = AdminComprobanteSerializer(qs, many=True, context={'request': request}).data

        # Stats
        total = ComprobantePago.objects.count()
        pendientes = ComprobantePago.objects.filter(estado='pendiente').count()

        return Response({
            'comprobantes': data,
            'total': total,
            'pendientes': pendientes,
        })


class AdminValidarComprobanteView(APIView):
    """Aprobar o rechazar un comprobante."""
    permission_classes = [IsAdminUser]

    def patch(self, request, comprobante_id):
        try:
            comprobante = ComprobantePago.objects.get(pk=comprobante_id)
        except ComprobantePago.DoesNotExist:
            return Response({"error": "Comprobante no encontrado."}, status=404)

        nuevo_estado = request.data.get('estado')
        if nuevo_estado not in ['aprobado', 'rechazado']:
            return Response({"error": "Estado debe ser 'aprobado' o 'rechazado'."}, status=400)

        # La lógica vive en pagos.services para que el back office haga
        # exactamente lo mismo al validar desde su propia pantalla.
        validar_comprobante(
            comprobante, nuevo_estado, request.user, request.data.get('nota', '')
        )

        return Response({
            'mensaje': f'Comprobante {nuevo_estado}. Reservas actualizadas.',
            'comprobante': AdminComprobanteSerializer(comprobante).data,
        })
