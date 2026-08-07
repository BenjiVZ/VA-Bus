"""Datos que la plantilla base necesita en todas las pantallas del back office.

Se calculan solo dentro de `/panel/` para no cargar consultas de más en la API
ni en el admin.
"""


def barra_lateral(request):
    ruta = request.path or ''
    if not ruta.startswith('/panel/'):
        return {}

    usuario = getattr(request, 'user', None)
    if not (usuario and usuario.is_authenticated and usuario.is_staff):
        return {}

    from pagos.models import ComprobantePago
    from viajes.models import ConfiguracionGeneral

    config = ConfiguracionGeneral.load()
    return {
        'pendientes_comprobantes': ComprobantePago.objects.filter(estado='pendiente').count(),
        'tasa_bcv': config.tasa_bcv if config else None,
    }
