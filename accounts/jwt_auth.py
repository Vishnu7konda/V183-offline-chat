"""
Accounts — JWT Authentication Middleware for Django Channels
Validates JWT tokens from WebSocket query strings.
"""
import jwt
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import User, AnonymousUser
from django.conf import settings
from urllib.parse import parse_qs


@database_sync_to_async
def get_user_from_token(token):
    """Decode JWT and return the corresponding User, or AnonymousUser on failure."""
    try:
        secret = getattr(settings, 'JWT_SECRET_KEY', settings.SECRET_KEY)
        payload = jwt.decode(token, secret, algorithms=['HS256'])
        user = User.objects.get(id=payload['user_id'])
        return user
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, User.DoesNotExist, KeyError):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    Custom middleware for Django Channels that authenticates WebSocket
    connections using a JWT token passed as a query parameter (?token=xxx).
    Falls back to session-based auth if no token is provided.
    """

    async def __call__(self, scope, receive, send):
        # Parse query string for token
        query_string = scope.get('query_string', b'').decode('utf-8')
        params = parse_qs(query_string)
        token_list = params.get('token', [])

        if token_list:
            token = token_list[0]
            scope['user'] = await get_user_from_token(token)
        else:
            # Fallback: if no token, check if session auth already set the user
            if 'user' not in scope or scope['user'].is_anonymous:
                scope['user'] = AnonymousUser()

        return await super().__call__(scope, receive, send)
