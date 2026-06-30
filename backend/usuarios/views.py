import threading

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Count, Max, Q
from .models import Usuario
from .serializers import RegistroSerializer, UsuarioSerializer, AdminClienteSerializer


def _enviar_email_codigo(email, asunto, mensaje_intro, codigo):
    """Envía (solo envía) el correo con un código ya generado. Pensado para
    ejecutarse en un hilo aparte: NO toca la base de datos."""
    html = f'''
    <div style="font-family:Inter,Arial,sans-serif;max-width:500px;margin:0 auto;background:#fff;">
        <div style="background:linear-gradient(135deg,#0a1628,#1a365d);padding:24px;text-align:center;border-radius:12px 12px 0 0;">
            <h1 style="color:#fff;margin:0;font-size:20px;">🚌 Aerorutas de Venezuela</h1>
        </div>
        <div style="padding:24px;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 12px 12px;">
            <p style="color:#4a5568;">{mensaje_intro}</p>
            <div style="background:#f0f4ff;border:2px dashed #0052cc;border-radius:12px;padding:20px;text-align:center;margin:20px 0;">
                <p style="margin:0 0 8px;color:#718096;font-size:13px;">Tu código de verificación:</p>
                <h2 style="margin:0;font-size:36px;letter-spacing:8px;color:#0052cc;font-weight:800;">{codigo}</h2>
            </div>
            <p style="color:#718096;font-size:13px;">Este código expira en <strong>15 minutos</strong>.</p>
            <p style="color:#718096;font-size:13px;">Si no solicitaste este código, ignora este mensaje.</p>
        </div>
    </div>'''

    try:
        send_mail(
            subject=asunto,
            message=f'{mensaje_intro}\n\nTu código: {codigo}\n\nExpira en 15 minutos.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f'[EMAIL ERROR] No se pudo enviar email a {email}: {e}')
        return False


def _enviar_codigo_email(usuario, asunto, mensaje_intro):
    """Genera el código de verificación y lo envía (de forma SÍNCRONA)."""
    codigo = usuario.generar_codigo(minutos=15)
    return _enviar_email_codigo(usuario.email, asunto, mensaje_intro, codigo)


def _enviar_codigo_email_async(usuario, asunto, mensaje_intro):
    """Genera el código (en DB, síncrono) y dispara el envío del correo en un
    hilo aparte para no bloquear la respuesta HTTP si el SMTP se cuelga."""
    codigo = usuario.generar_codigo(minutos=15)
    threading.Thread(
        target=_enviar_email_codigo,
        args=(usuario.email, asunto, mensaje_intro, codigo),
        daemon=True,
    ).start()


class RegistroView(generics.CreateAPIView):
    queryset = Usuario.objects.all()
    serializer_class = RegistroSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'registro'

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        requiere = getattr(settings, 'EMAIL_VERIFICATION_REQUIRED', False)
        verificacion_enviada = False

        if requiere and user.email:
            # Enviar código en segundo plano: el correo no debe bloquear la
            # respuesta (si el SMTP se cuelga daba 504). El código queda en DB.
            _enviar_codigo_email_async(
                user,
                '📧 Verifica tu email — Aerorutas de Venezuela',
                f'Hola <strong>{user.first_name or user.username}</strong>, ingresa este código para verificar tu email.'
            )
            verificacion_enviada = True
        else:
            # Verificación desactivada: la cuenta queda lista para usar de una.
            if not user.email_verificado:
                user.email_verificado = True
                user.save(update_fields=['email_verificado'])

        return Response({
            "mensaje": "Usuario registrado exitosamente.",
            "usuario": UsuarioSerializer(user).data,
            "requiere_verificacion": requiere,
            "verificacion_enviada": verificacion_enviada,
        }, status=status.HTTP_201_CREATED)


class VerificarEmailView(APIView):
    """Verifica el email del usuario con el código de 6 dígitos."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip()
        codigo = request.data.get('codigo', '').strip()

        if not email or not codigo:
            return Response(
                {"error": "Email y código son requeridos."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            return Response(
                {"error": "No se encontró un usuario con ese email."},
                status=status.HTTP_404_NOT_FOUND
            )

        if user.email_verificado:
            return Response({"mensaje": "El email ya está verificado."})

        if not user.verificar_codigo(codigo):
            return Response(
                {"error": "Código inválido o expirado. Solicita uno nuevo."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.email_verificado = True
        user.save(update_fields=['email_verificado'])
        user.limpiar_codigo()

        return Response({"mensaje": "Email verificado exitosamente. ✅"})


class ReenviarCodigoView(APIView):
    """Reenvía el código de verificación de email."""
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'registro'

    def post(self, request):
        email = request.data.get('email', '').strip()
        if not email:
            return Response(
                {"error": "Email es requerido."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            # No revelamos si el email existe o no (seguridad)
            return Response({"mensaje": "Si el email existe, se envió un nuevo código."})

        if user.email_verificado:
            return Response({"mensaje": "El email ya está verificado."})

        _enviar_codigo_email_async(
            user,
            '📧 Nuevo código de verificación — Aerorutas de Venezuela',
            f'Hola <strong>{user.first_name or user.username}</strong>, aquí tienes un nuevo código de verificación.'
        )

        return Response({"mensaje": "Si el email existe, se envió un nuevo código."})


class SolicitarResetPasswordView(APIView):
    """Envía un código de recuperación de contraseña por email."""
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request):
        email = request.data.get('email', '').strip()
        if not email:
            return Response(
                {"error": "Email es requerido."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            # No revelamos si el email existe (seguridad)
            return Response({
                "mensaje": "Si el email está registrado, recibirás un código de recuperación."
            })

        _enviar_codigo_email_async(
            user,
            '🔑 Recuperar contraseña — Aerorutas de Venezuela',
            f'Hola <strong>{user.first_name or user.username}</strong>, ingresa este código para restablecer tu contraseña.'
        )

        return Response({
            "mensaje": "Si el email está registrado, recibirás un código de recuperación."
        })


class ResetPasswordView(APIView):
    """Restablece la contraseña usando el código enviado por email."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip()
        codigo = request.data.get('codigo', '').strip()
        new_password = request.data.get('new_password', '')
        new_password2 = request.data.get('new_password2', '')

        if not all([email, codigo, new_password, new_password2]):
            return Response(
                {"error": "Todos los campos son requeridos."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(new_password) < 6:
            return Response(
                {"error": "La contraseña debe tener al menos 6 caracteres."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_password != new_password2:
            return Response(
                {"error": "Las contraseñas no coinciden."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            return Response(
                {"error": "No se encontró un usuario con ese email."},
                status=status.HTTP_404_NOT_FOUND
            )

        if not user.verificar_codigo(codigo):
            return Response(
                {"error": "Código inválido o expirado. Solicita uno nuevo."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.email_verificado = True  # Si resetea con código, el email está verificado
        user.save()
        user.limpiar_codigo()

        return Response({"mensaje": "Contraseña restablecida exitosamente. Ya puedes iniciar sesión."})


class PerfilView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UsuarioSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = UsuarioSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request):
        return self.put(request)


class CambiarPasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        current = request.data.get('current_password', '')
        new_pass = request.data.get('new_password', '')
        new_pass2 = request.data.get('new_password2', '')

        if not request.user.check_password(current):
            return Response(
                {"error": "La contraseña actual es incorrecta."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(new_pass) < 6:
            return Response(
                {"error": "La nueva contraseña debe tener al menos 6 caracteres."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_pass != new_pass2:
            return Response(
                {"error": "Las contraseñas nuevas no coinciden."},
                status=status.HTTP_400_BAD_REQUEST
            )

        request.user.set_password(new_pass)
        request.user.save()
        return Response({"mensaje": "Contraseña actualizada exitosamente."})


class GoogleLoginView(APIView):
    """Login/Registro con Google. Recibe el credential (ID token) de Google."""
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request):
        credential = request.data.get('credential')
        if not credential:
            return Response(
                {"error": "Token de Google no proporcionado."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests as google_requests

            google_client_id = getattr(settings, 'GOOGLE_CLIENT_ID', '')
            if not google_client_id:
                return Response(
                    {"error": "Google login no está configurado."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            idinfo = id_token.verify_oauth2_token(
                credential,
                google_requests.Request(),
                google_client_id,
                clock_skew_in_seconds=10  # Tolerancia de reloj de 10 segundos
            )

            email = idinfo.get('email')
            if not email or not idinfo.get('email_verified'):
                return Response(
                    {"error": "Email de Google no verificado."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except ValueError as e:
            return Response(
                {"error": f"Token de Google inválido: {str(e)}"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        first_name = idinfo.get('given_name', '')
        last_name = idinfo.get('family_name', '')

        user, created = Usuario.objects.get_or_create(
            email=email,
            defaults={
                'username': email.split('@')[0],
                'first_name': first_name,
                'last_name': last_name,
                'email_verificado': True,  # Google ya verificó el email
            }
        )

        if not created:
            if not user.first_name and first_name:
                user.first_name = first_name
            if not user.last_name and last_name:
                user.last_name = last_name
            if not user.email_verificado:
                user.email_verificado = True
            user.save()

        if created:
            base_username = email.split('@')[0]
            username = base_username
            counter = 1
            while Usuario.objects.filter(username=username).exclude(pk=user.pk).exists():
                username = f"{base_username}{counter}"
                counter += 1
            if username != user.username:
                user.username = username
                user.save()

        refresh = RefreshToken.for_user(user)
        tokens = {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }

        return Response({
            'tokens': tokens,
            'usuario': UsuarioSerializer(user).data,
            'nuevo_usuario': created,
        }, status=status.HTTP_200_OK)


# ═══════════════════════════════════════════════════════
#  Admin — Dashboard de Clientes
# ═══════════════════════════════════════════════════════

class ClientesDashboardView(APIView):
    """Estadísticas globales + Top 10 pasajeros frecuentes."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        from reservas.models import Reserva

        total_clientes = Usuario.objects.filter(is_staff=False).count()

        # Clientes que tienen al menos 1 reserva confirmada
        compradores = (
            Reserva.objects.filter(estado='confirmada')
            .values('usuario')
            .distinct()
            .count()
        )

        vip_activos = Usuario.objects.filter(es_vip=True, is_staff=False).count()

        # Top 10 pasajeros por reservas confirmadas
        top_pasajeros_qs = (
            Usuario.objects.filter(is_staff=False)
            .annotate(
                total_viajes=Count(
                    'reservas',
                    filter=Q(reservas__estado='confirmada')
                ),
                ultimo_viaje=Max(
                    'reservas__viaje__fecha_salida',
                    filter=Q(reservas__estado='confirmada')
                ),
            )
            .filter(total_viajes__gt=0)
            .order_by('-total_viajes')[:10]
        )

        top_pasajeros = AdminClienteSerializer(top_pasajeros_qs, many=True).data

        return Response({
            'total_clientes': total_clientes,
            'compradores': compradores,
            'vip_activos': vip_activos,
            'top_pasajeros': top_pasajeros,
        })


class AdminClientesListView(APIView):
    """Lista paginada de clientes con búsqueda por nombre/cédula/email."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        from reservas.models import Reserva

        q = request.query_params.get('q', '').strip()

        qs = Usuario.objects.filter(is_staff=False).annotate(
            total_viajes=Count(
                'reservas',
                filter=Q(reservas__estado='confirmada')
            ),
            ultimo_viaje=Max(
                'reservas__viaje__fecha_salida',
                filter=Q(reservas__estado='confirmada')
            ),
        )

        if q:
            qs = qs.filter(
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(cedula__icontains=q) |
                Q(email__icontains=q) |
                Q(username__icontains=q)
            )

        qs = qs.order_by('-total_viajes', '-date_joined')[:50]

        return Response(AdminClienteSerializer(qs, many=True).data)


class AdminToggleVipView(APIView):
    """Actualizar estado VIP de un cliente."""
    permission_classes = [permissions.IsAdminUser]

    def patch(self, request, user_id):
        try:
            usuario = Usuario.objects.get(pk=user_id, is_staff=False)
        except Usuario.DoesNotExist:
            return Response(
                {"error": "Cliente no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )

        es_vip = request.data.get('es_vip')
        servicio_vip = request.data.get('servicio_vip')
        notas_admin = request.data.get('notas_admin')

        if es_vip is not None:
            usuario.es_vip = bool(es_vip)
        if servicio_vip is not None:
            if servicio_vip in dict(Usuario.SERVICIO_VIP_CHOICES):
                usuario.servicio_vip = servicio_vip
        if notas_admin is not None:
            usuario.notas_admin = notas_admin

        # Si se desactiva VIP, resetear servicio
        if not usuario.es_vip:
            usuario.servicio_vip = 'ninguno'

        usuario.save()

        # Re-annotate for serializer
        from reservas.models import Reserva
        usuario_qs = Usuario.objects.filter(pk=usuario.pk).annotate(
            total_viajes=Count('reservas', filter=Q(reservas__estado='confirmada')),
            ultimo_viaje=Max('reservas__viaje__fecha_salida', filter=Q(reservas__estado='confirmada')),
        ).first()

        return Response(AdminClienteSerializer(usuario_qs).data)

