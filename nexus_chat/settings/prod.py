"""
V-OFFLINE CHAT — Production Settings
Compatible with Vercel, Render, and other cloud platforms.
"""
import os
from .base import *  # noqa: F401,F403

DEBUG = False

SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-prod-fallback-change-me')

# ── Allowed Hosts ──────────────────────────────────────────────
_raw_hosts = os.environ.get('ALLOWED_HOSTS', '.onrender.com,.vercel.app')
ALLOWED_HOSTS = [h.strip() for h in _raw_hosts.split(',') if h.strip()]
ALLOWED_HOSTS += ['localhost', '127.0.0.1', 'v183-oc.vercel.app']

import dj_database_url

# ── PostgreSQL Database ────────────────────────────────────────
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite3'),
        conn_max_age=600
    )
}

# ── Channel Layer ──────────────────────────────────────────────
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}

# ── Static Files (WhiteNoise) ──────────────────────────────────
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# ── Sessions (DB-backed — works on serverless) ─────────────────
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# ── Security ───────────────────────────────────────────────────
SECURE_SSL_REDIRECT = False   # Vercel handles HTTPS termination
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

CSRF_TRUSTED_ORIGINS = [
    'https://v183-oc.vercel.app',
    'https://*.vercel.app',
    'https://*.onrender.com',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

