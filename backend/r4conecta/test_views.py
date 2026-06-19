"""
Vistas de PRUEBA para validar la conexión con R4 Conecta (Débito Inmediato OTP).

Acceso:
- En DESARROLLO (DEBUG=True): abierto, sin login (herramienta de dev).
- En PRODUCCIÓN (DEBUG=False): SOLO superusuarios logueados (sesión del admin).
  Así se puede probar en prod sin activar DEBUG ni exponer la herramienta al público.

⚠️ Débito Inmediato mueve fondos reales: usar con cuidado.
"""
from django.conf import settings
from django.shortcuts import render
from django.contrib.auth.views import redirect_to_login
from django.views.decorators.csrf import ensure_csrf_cookie

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework.authentication import SessionAuthentication

from . import services


def _acceso_ok(request) -> bool:
    """True si DEBUG está activo o el usuario es superusuario autenticado."""
    if getattr(settings, 'DEBUG', False):
        return True
    user = getattr(request, 'user', None)
    return bool(user and user.is_authenticated and user.is_superuser)


class IsSuperuserOrDebug(permissions.BasePermission):
    """Permite acceso en DEBUG o a superusuarios autenticados."""
    message = 'Solo superusuarios pueden usar la herramienta de prueba.'

    def has_permission(self, request, view):
        return _acceso_ok(request)


@ensure_csrf_cookie
def test_page(request):
    """Página HTML de prueba (deja la cookie csrftoken para los POST)."""
    if not _acceso_ok(request):
        # Mandar al login del admin y volver acá tras autenticarse.
        return redirect_to_login(request.get_full_path(), '/admin/login/')
    return render(request, 'r4conecta/test.html')


class _TestBase(APIView):
    # Sesión del admin (cookie) — el front envía el token CSRF en los POST.
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsSuperuserOrDebug]
    throttle_classes = []


class TestGenerarOtp(_TestBase):
    def post(self, request):
        d = request.data
        try:
            resp = services.generar_otp(
                d.get('banco', ''), d.get('monto', '0'),
                d.get('telefono', ''), d.get('cedula', ''))
        except services.R4Error as e:
            return Response({'ok': False, 'error': e.message}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({'ok': True, 'response': resp})


class TestDebito(_TestBase):
    def post(self, request):
        d = request.data
        try:
            resp = services.debito_inmediato(
                d.get('banco', ''), d.get('monto', '0'), d.get('telefono', ''),
                d.get('cedula', ''), d.get('nombre', ''), d.get('otp', ''),
                d.get('concepto', ''))
        except services.R4Error as e:
            return Response({'ok': False, 'error': e.message}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({'ok': True, 'response': resp})


class TestConsultar(_TestBase):
    def post(self, request):
        operacion_id = request.data.get('id', '')
        if not operacion_id:
            return Response({'ok': False, 'error': 'Falta el id.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            resp = services.consultar_operacion(operacion_id)
        except services.R4Error as e:
            return Response({'ok': False, 'error': e.message}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({'ok': True, 'response': resp})


class TestDomiciliacionTelefono(_TestBase):
    """PRUEBA: afiliación por teléfono (DomiciliacionCELE). 1er envío afilia sin cobrar."""
    def post(self, request):
        d = request.data
        try:
            resp = services.domiciliacion_telefono(
                d.get('docId', ''), d.get('telefono', ''), d.get('nombre', ''),
                d.get('banco', ''), d.get('monto', '1.00'), d.get('concepto', ''))
        except services.R4Error as e:
            return Response({'ok': False, 'error': e.message}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({'ok': True, 'response': resp})
