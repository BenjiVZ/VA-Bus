"""Aerorutas URL Configuration"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic import RedirectView

admin.site.site_header = "Aerorutas de Venezuela — Datos y configuración"
admin.site.site_title = "Aerorutas — Datos"
admin.site.index_title = "Datos y configuración"

urlpatterns = [
    # ── Enlaces viejos ──
    # Estas pantallas vivían bajo /admin/. Van ANTES del admin porque su
    # URLconf termina en un catch-all que si no devolvería 404.
    path('admin/caja/', RedirectView.as_view(url='/panel/caja/')),
    path('admin/portal-viajes/', RedirectView.as_view(url='/panel/viajes/')),
    path('admin/r4-pagos/', RedirectView.as_view(url='/panel/pagos-r4/')),

    # Back office propio (todas las pantallas del personal).
    path('panel/', include('backoffice.urls')),

    # El admin de Django queda solo para tocar datos crudos.
    path('admin/', admin.site.urls),

    path('api/', include('viajes.urls')),
    path('api/', include('reservas.urls')),
    path('api/', include('pagos.urls')),
    path('api/auth/', include('usuarios.urls')),
    path('api/externo/', include('api_externa.urls')),
    path('api/r4/', include('r4conecta.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # daphne no sirve estáticos como runserver: los servimos aquí en desarrollo
    # (necesario para que el CSS/imágenes carguen).
    urlpatterns += staticfiles_urlpatterns()
