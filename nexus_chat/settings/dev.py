"""
V-OFFLINE CHAT — Development Settings
Uses MongoDB via djongo connector.
"""
from .base import *  # noqa: F401,F403

DEBUG = True

ALLOWED_HOSTS = ['*']  # Allow all connections for local network testing

# ── SQLite Database (for dev) ─────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
print('[Nexus] Using SQLite database')

# ── Channel layer — in-memory for development (no Redis needed) ──
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}
