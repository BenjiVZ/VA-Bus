from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone

from .models import MetodoPago, ComprobantePago
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
        metodos = MetodoPago.objects.filter(activo=True).prefetch_related('datos')
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

        # Verify metodo_pago exists
        try:
            metodo = MetodoPago.objects.get(pk=metodo_pago_id, activo=True)
        except MetodoPago.DoesNotExist:
            return Response(
                {"error": "Método de pago no válido."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create comprobante
        comprobante = ComprobantePago.objects.create(
            grupo_pago=grupo_pago,
            usuario=request.user,
            metodo_pago=metodo,
            numero_referencia=serializer.validated_data.get('numero_referencia', ''),
            imagen=serializer.validated_data['imagen'],
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

        data = AdminComprobanteSerializer(qs, many=True).data

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

        comprobante.estado = nuevo_estado
        comprobante.revisado_por = request.user
        comprobante.fecha_revision = timezone.now()
        comprobante.nota_admin = request.data.get('nota', '')
        comprobante.save()

        # Update associated reservations
        reservas = Reserva.objects.filter(grupo_pago=comprobante.grupo_pago)
        if nuevo_estado == 'aprobado':
            reservas.update(estado='confirmado')
        elif nuevo_estado == 'rechazado':
            reservas.update(estado='cancelado')

        return Response({
            'mensaje': f'Comprobante {nuevo_estado}. Reservas actualizadas.',
            'comprobante': AdminComprobanteSerializer(comprobante).data,
        })
