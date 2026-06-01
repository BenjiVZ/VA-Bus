"""
ASGI config for config project.

Enrutamiento por protocolo:
- HTTP → Django ASGI normal (todas las views REST siguen funcionando igual).
- WebSocket → Channels (rutas definidas en viajes/routing.py).
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# IMPORTANTE: get_asgi_application() debe llamarse ANTES de cualquier import
# que toque modelos/apps (sino Django no está listo).
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.auth import AuthMiddlewareStack  # noqa: E402

from viajes.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns),
    ),
})
