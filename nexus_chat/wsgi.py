"""
WSGI config for V-OFFLINE CHAT.
Vercel entry point — uses prod settings when DJANGO_SETTINGS_MODULE is set.
"""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nexus_chat.settings.prod')
application = get_wsgi_application()
