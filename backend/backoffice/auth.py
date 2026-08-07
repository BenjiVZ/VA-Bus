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
