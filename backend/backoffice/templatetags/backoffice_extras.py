"""Utilidades de plantilla del back office."""
import os

from django import template
from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()

# Se calcula una vez por proceso: el servicio se reinicia en cada despliegue,
# así que la versión se renueva sola cuando el archivo cambia.
_versiones = {}


def _version(ruta):
    if ruta in _versiones:
        return _versiones[ruta]

    marca = ''
    candidatos = []
    if getattr(settings, 'STATIC_ROOT', None):
        candidatos.append(os.path.join(settings.STATIC_ROOT, *ruta.split('/')))
    encontrado = finders.find(ruta)
    if encontrado:
        candidatos.append(encontrado)

    for ruta_fs in candidatos:
        try:
            marca = str(int(os.path.getmtime(ruta_fs)))
            break
        except OSError:
            continue

    _versiones[ruta] = marca
    return marca


@register.simple_tag
def estatico_versionado(ruta):
    """URL de un estático con `?v=<fecha del archivo>`.

    Sin esto, tras un despliegue Cloudflare y el navegador siguen sirviendo la
    copia vieja durante horas: la URL no cambia, así que nadie se entera de que
    el archivo cambió. Con la marca de tiempo, cada versión es una URL nueva.
    """
    url = static(ruta)
    marca = _version(ruta)
    if not marca:
        return url
    separador = '&' if '?' in url else '?'
    return f'{url}{separador}v={marca}'
