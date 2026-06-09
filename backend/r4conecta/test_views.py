"""
Vistas de PRUEBA para validar la conexión con R4 Conecta (Débito Inmediato OTP).

⚠️ Solo disponibles con settings.DEBUG=True. Llaman directamente al banco con el
monto que se escriba (NO usan reservas ni autenticación). Débito Inmediato mueve
fondos reales: usar con cuidado.
"""
from django.conf import settings
from django.shortcuts import render
from django.http import HttpResponseForbidden

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status

from . import services


def _debug_on():
    return bool(getattr(settings, 'DEBUG', False))


def test_page(request):
    """Página HTML de prueba."""
    if not _debug_on():
        return HttpResponseForbidden('Disponible solo en modo DEBUG.')
    return render(request, 'r4conecta/test.html')


class _TestBase(APIView):
    authentication_classes = []          # sin JWT/sesión/CSRF (herramienta de dev)
    permission_classes = [permissions.AllowAny]
    throttle_classes = []

    def _guard(self):
        return None if _debug_on() else Response(
            {'ok': False, 'error': 'Solo disponible en modo DEBUG.'},
            status=status.HTTP_403_FORBIDDEN)


class TestGenerarOtp(_TestBase):
    def post(self, request):
        g = self._guard()
        if g:
            return g
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
        g = self._guard()
        if g:
            return g
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
        g = self._guard()
        if g:
            return g
        operacion_id = request.data.get('id', '')
        if not operacion_id:
            return Response({'ok': False, 'error': 'Falta el id.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            resp = services.consultar_operacion(operacion_id)
        except services.R4Error as e:
            return Response({'ok': False, 'error': e.message}, status=status.HTTP_502_BAD_GATEWAY)
        return Response({'ok': True, 'response': resp})
