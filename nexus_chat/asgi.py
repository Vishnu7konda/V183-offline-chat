"""
ASGI config for V-OFFLINE CHAT.
Routes HTTP and WebSocket connections.
Uses JWT authentication middleware for WebSocket connections.
"""
import os
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nexus_chat.settings.dev')

django_asgi_app = get_asgi_application()

from chat.routing import websocket_urlpatterns  # noqa: E402
from accounts.jwt_auth import JWTAuthMiddleware  # noqa: E402

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        JWTAuthMiddleware(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
