"""
Chat — WebSocket Routing
"""
from django.urls import re_path
from . import consumers
from . import presence

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<conversation_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/presence/$', presence.PresenceConsumer.as_asgi()),
]
