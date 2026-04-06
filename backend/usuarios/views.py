from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from django.conf import settings
from django.core.mail import send_mail
from .models import Usuario
from .serializers import RegistroSerializer, UsuarioSerializer


def _enviar_codigo_email(usuario, asunto, mensaje_intro):
    """Envía un código de verificación por email."""
    codigo = usuario.generar_codigo(minutos=15)
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
            recipient_list=[usuario.email],
            html_message=html,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f'[EMAIL ERROR] No se pudo enviar email a {usuario.email}: {e}')
        return False


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

        # Enviar código de verificación de email
        email_enviado = False
        if user.email:
            email_enviado = _enviar_codigo_email(
                user,
                '📧 Verifica tu email — Aerorutas de Venezuela',
                f'Hola <strong>{user.first_name or user.username}</strong>, ingresa este código para verificar tu email.'
            )

        return Response({
            "mensaje": "Usuario registrado exitosamente.",
            "usuario": UsuarioSerializer(user).data,
            "verificacion_enviada": email_enviado,
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

        _enviar_codigo_email(
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

        _enviar_codigo_email(
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
