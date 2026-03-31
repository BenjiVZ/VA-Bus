from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings as django_settings

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

        comprobante.estado = nuevo_estado
        comprobante.revisado_por = request.user
        comprobante.fecha_revision = timezone.now()
        comprobante.nota_admin = request.data.get('nota', '')
        comprobante.save()

        # Update associated reservations
        reservas = Reserva.objects.filter(grupo_pago=comprobante.grupo_pago)
        if nuevo_estado == 'aprobado':
            reservas.update(estado='confirmado')
            # Re-save each to generate ticket codes
            for r in reservas:
                r.estado = 'confirmado'
                r.save()
        elif nuevo_estado == 'rechazado':
            reservas.update(estado='cancelado')

        # ── Send email notification ──
        self._enviar_email_notificacion(comprobante, reservas, nuevo_estado)

        return Response({
            'mensaje': f'Comprobante {nuevo_estado}. Reservas actualizadas.',
            'comprobante': AdminComprobanteSerializer(comprobante).data,
        })

    def _enviar_email_notificacion(self, comprobante, reservas, estado):
        """Envía email al usuario notificando el resultado de su pago."""
        usuario = comprobante.usuario
        email = usuario.email
        if not email:
            return

        reservas_list = reservas.select_related('viaje__ruta', 'viaje__autobus')
        primera = reservas_list.first()

        if estado == 'aprobado':
            subject = '✅ Pago Aprobado — Aerorutas de Venezuela'
            # Build ticket info
            asientos_info = ''
            for r in reservas_list:
                ticket = r.codigo_ticket or 'Pendiente'
                asientos_info += f'''
                <tr>
                    <td style="padding:8px 12px;border-bottom:1px solid #eee;">Asiento #{r.numero_asiento} (Piso {r.piso_asiento})</td>
                    <td style="padding:8px 12px;border-bottom:1px solid #eee;">{r.nombre_pasajero or usuario.get_full_name() or usuario.username}</td>
                    <td style="padding:8px 12px;border-bottom:1px solid #eee;font-weight:700;color:#0052cc;">{ticket}</td>
                </tr>'''

            viaje_info = ''
            if primera and primera.viaje:
                v = primera.viaje
                viaje_info = f'{v.ruta.origen} → {v.ruta.destino} · {v.fecha_salida} · {v.hora_salida}'

            html = f'''
            <div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;background:#fff;">
                <div style="background:linear-gradient(135deg,#0a1628,#1a365d);padding:24px;text-align:center;border-radius:12px 12px 0 0;">
                    <h1 style="color:#fff;margin:0;font-size:20px;">🚌 Aerorutas de Venezuela</h1>
                </div>
                <div style="padding:24px;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 12px 12px;">
                    <h2 style="color:#22543d;margin-top:0;">✅ ¡Tu pago ha sido aprobado!</h2>
                    <p style="color:#4a5568;">Hola <strong>{usuario.first_name or usuario.username}</strong>, tu comprobante de pago fue verificado exitosamente.</p>

                    <div style="background:#f7fafc;border:1px solid #e2e8f0;border-radius:8px;padding:16px;margin:16px 0;">
                        <p style="margin:0 0 4px;font-size:13px;color:#718096;">VIAJE</p>
                        <p style="margin:0;font-weight:700;color:#1a365d;">{viaje_info}</p>
                    </div>

                    <table style="width:100%;border-collapse:collapse;margin:16px 0;">
                        <thead>
                            <tr style="background:#f7fafc;">
                                <th style="padding:8px 12px;text-align:left;font-size:13px;color:#718096;">Asiento</th>
                                <th style="padding:8px 12px;text-align:left;font-size:13px;color:#718096;">Pasajero</th>
                                <th style="padding:8px 12px;text-align:left;font-size:13px;color:#718096;">Código Ticket</th>
                            </tr>
                        </thead>
                        <tbody>{asientos_info}</tbody>
                    </table>

                    <p style="color:#4a5568;font-size:14px;">Presenta tu código de ticket al momento de abordar. ¡Buen viaje! 🎉</p>
                </div>
            </div>'''
        else:
            nota = comprobante.nota_admin or 'No se proporcionó motivo.'
            html = f'''
            <div style="font-family:Inter,Arial,sans-serif;max-width:600px;margin:0 auto;background:#fff;">
                <div style="background:linear-gradient(135deg,#0a1628,#1a365d);padding:24px;text-align:center;border-radius:12px 12px 0 0;">
                    <h1 style="color:#fff;margin:0;font-size:20px;">🚌 Aerorutas de Venezuela</h1>
                </div>
                <div style="padding:24px;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 12px 12px;">
                    <h2 style="color:#742a2a;margin-top:0;">❌ Comprobante Rechazado</h2>
                    <p style="color:#4a5568;">Hola <strong>{usuario.first_name or usuario.username}</strong>, lamentamos informarte que tu comprobante de pago no fue aprobado.</p>

                    <div style="background:#fff5f5;border:1px solid #fed7d7;border-radius:8px;padding:16px;margin:16px 0;">
                        <p style="margin:0 0 4px;font-size:13px;color:#718096;">MOTIVO</p>
                        <p style="margin:0;color:#742a2a;">{nota}</p>
                    </div>

                    <p style="color:#4a5568;font-size:14px;">Puedes intentar nuevamente realizando una nueva reserva y subiendo un comprobante válido.</p>
                </div>
            </div>'''

        try:
            send_mail(
                subject=subject,
                message='',  # Plain text fallback
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                html_message=html,
                fail_silently=False,
            )
        except Exception as e:
            print(f'[EMAIL ERROR] No se pudo enviar email a {email}: {e}')

