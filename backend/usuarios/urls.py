from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework.throttling import ScopedRateThrottle
from .views import (
    RegistroView, PerfilView, CambiarPasswordView, GoogleLoginView,
    VerificarEmailView, ReenviarCodigoView,
    SolicitarResetPasswordView, ResetPasswordView,
)


class LoginThrottledView(TokenObtainPairView):
    """Login con rate-limiting: maximo 5 intentos por minuto."""
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'


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
]
