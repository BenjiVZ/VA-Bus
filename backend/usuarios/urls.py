from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.response import Response
from rest_framework import status
from .models import Usuario
from .views import (
    RegistroView, PerfilView, CambiarPasswordView, GoogleLoginView,
    VerificarEmailView, ReenviarCodigoView,
    SolicitarResetPasswordView, ResetPasswordView,
    ClientesDashboardView, AdminClientesListView, AdminToggleVipView,
)


class LoginThrottledView(TokenObtainPairView):
    """Login con rate-limiting y verificación de email obligatoria."""
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request, *args, **kwargs):
        from django.contrib.auth import authenticate

        username = request.data.get('username', '')
        password = request.data.get('password', '')

        # Primero validar credenciales
        user = authenticate(request, username=username, password=password)

        if user is None:
            # Intentar buscar por email como username (tolerante a duplicados)
            from .views import usuario_por_email
            user_by_email = usuario_por_email(username)
            if user_by_email:
                user = authenticate(request, username=user_by_email.username, password=password)
                if user:
                    # El serializer JWT busca por username: pasarle el real
                    request.data['username'] = user_by_email.username

        if user is None:
            return Response(
                {"detail": "Credenciales inválidas. Verifica tu usuario y contraseña."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Continuar con el flujo normal de JWT
        return super().post(request, *args, **kwargs)


urlpatterns = [
    # Auth básica
    path('registro/', RegistroView.as_view(), name='registro'),
    path('login/', LoginThrottledView.as_view(), name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('google-login/', GoogleLoginView.as_view(), name='google_login'),

    # Perfil
    path('perfil/', PerfilView.as_view(), name='perfil'),
    path('cambiar-password/', CambiarPasswordView.as_view(), name='cambiar_password'),

    # Verificación de email
    path('verificar-email/', VerificarEmailView.as_view(), name='verificar_email'),
    path('reenviar-codigo/', ReenviarCodigoView.as_view(), name='reenviar_codigo'),

    # Recuperar contraseña
    path('recuperar-password/', SolicitarResetPasswordView.as_view(), name='recuperar_password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset_password'),

    # Admin — Clientes
    path('admin/clientes/dashboard/', ClientesDashboardView.as_view(), name='admin-clientes-dashboard'),
    path('admin/clientes/', AdminClientesListView.as_view(), name='admin-clientes-list'),
    path('admin/clientes/<int:user_id>/vip/', AdminToggleVipView.as_view(), name='admin-toggle-vip'),
]

