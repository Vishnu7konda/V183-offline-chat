"""
WSGI config for V-OFFLINE CHAT.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nexus_chat.settings.dev')
application = get_wsgi_application()
