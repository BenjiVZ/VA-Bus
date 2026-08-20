"""Control de acceso del back office.

Mismo criterio que el admin (`is_staff`), pero mandando al login propio en
lugar del de Django, para que el personal no salte entre dos pantallas de
ingreso distintas.
"""
from functools import wraps
from urllib.parse import urlencode

from django.shortcuts import redirect
from django.urls import reverse


def staff_requerido(vista):
    """Deja pasar solo a usuarios activos del personal."""
    @wraps(vista)
    def _envoltura(request, *args, **kwargs):
        usuario = request.user
        if usuario.is_authenticated and usuario.is_active and usuario.is_staff:
            return vista(request, *args, **kwargs)
        destino = reverse('backoffice:ingresar')
        return redirect(f'{destino}?{urlencode({"next": request.get_full_path()})}')
    return _envoltura


def superusuario_requerido(vista):
    """Solo administradores.

    Dar de alta cuentas del personal es repartir permisos: si cualquier
    empleado con acceso al back office pudiera hacerlo, podría crearse a sí
    mismo un administrador. Al personal que no lo es se le devuelve al inicio
    con un aviso, en vez de mandarlo al login (ya entró; lo que falta es rango).
    """
    @wraps(vista)
    def _envoltura(request, *args, **kwargs):
        usuario = request.user
        if usuario.is_authenticated and usuario.is_active and usuario.is_superuser:
            return vista(request, *args, **kwargs)
        if usuario.is_authenticated and usuario.is_staff:
            from django.contrib import messages
            messages.error(request, 'Esa pantalla es solo para administradores.')
            return redirect(reverse('backoffice:inicio'))
        destino = reverse('backoffice:ingresar')
        return redirect(f'{destino}?{urlencode({"next": request.get_full_path()})}')
    return _envoltura
