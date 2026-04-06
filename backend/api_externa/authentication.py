"""
Autenticación por API Key para el sistema externo de control.

El sistema externo debe enviar el header:
    X-API-KEY: <clave>

Esto permite acceso a los endpoints de /api/externo/ sin necesidad
de un usuario Django o tokens JWT.
"""

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings


class ExternalAPIUser:
    """Usuario virtual para peticiones autenticadas por API Key."""
    is_authenticated = True
    is_staff = False
    is_superuser = False
    pk = None
    username = 'sistema_externo'

    def __str__(self):
        return 'Sistema Externo'


class APIKeyAuthentication(BaseAuthentication):
    """Autentica peticiones usando el header X-API-KEY."""

    def authenticate(self, request):
        api_key = request.META.get('HTTP_X_API_KEY', '').strip()

        if not api_key:
            return None  # No hay API key, se pasa al siguiente auth

        expected_key = getattr(settings, 'EXTERNAL_API_KEY', '')
        if not expected_key:
            raise AuthenticationFailed('API externa no configurada.')

        if api_key != expected_key:
            raise AuthenticationFailed('API Key inválida.')

        return (ExternalAPIUser(), None)
