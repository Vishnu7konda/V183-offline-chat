"""
Chat — WebSocket Presence System
Real-time nearby user discovery via WebSocket.
Maintains an in-memory dict of active users and broadcasts updates.
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

# In-memory active users store: {channel_name: {user_id, username, avatar, ip}}
ACTIVE_USERS = {}


class PresenceConsumer(AsyncWebsocketConsumer):
    """
    Handles WebSocket connections for the presence/nearby system.
    Each authenticated client connects on page load:
    - connect(): registers user in ACTIVE_USERS, joins 'presence' group, broadcasts
    - disconnect(): removes user from ACTIVE_USERS, broadcasts
    - receive(): handles heartbeat pings
    """

    async def connect(self):
        self.user = self.scope['user']

        if self.user.is_anonymous:
            await self.close()
            return

        self.group_name = 'presence'

        # Get user info
        user_info = await self.get_user_info()

        # Get client IP from scope headers
        client_ip = '0.0.0.0'
        if self.scope.get('client'):
            client_ip = self.scope['client'][0]
        # Check for X-Forwarded-For
        for header_name, header_value in self.scope.get('headers', []):
            if header_name == b'x-forwarded-for':
                client_ip = header_value.decode('utf-8').split(',')[0].strip()
                break

        # Register in active users
        ACTIVE_USERS[self.channel_name] = {
            'user_id': self.user.id,
            'username': user_info['display_name'],
            'avatar': user_info['avatar'],
            'ip': client_ip,
        }

        # Join presence group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Broadcast updated user list to all
        await self.broadcast_presence()

    async def disconnect(self, close_code):
        # Remove from active users
        ACTIVE_USERS.pop(self.channel_name, None)

        # Leave group
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

        # Broadcast updated list
        await self.broadcast_presence()

    async def receive(self, text_data):
        """Handle heartbeat or other client messages."""
        try:
            data = json.loads(text_data)
            if data.get('type') == 'heartbeat':
                # Just acknowledge — connection staying open is enough
                await self.send(text_data=json.dumps({'type': 'heartbeat_ack'}))
        except (json.JSONDecodeError, Exception):
            pass

    async def broadcast_presence(self):
        """Send updated active users list to all connected clients."""
        users_list = self.get_active_users_list()
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'presence_update',
                'users': users_list,
            }
        )

    async def presence_update(self, event):
        """Handler for presence_update group messages — send to client."""
        # Filter out the current user from the list they receive
        users = [u for u in event['users'] if u['user_id'] != self.user.id]
        await self.send(text_data=json.dumps({
            'type': 'presence_update',
            'users': users,
        }))

    @staticmethod
    def get_active_users_list():
        """Build a deduplicated list of active users from ACTIVE_USERS dict."""
        seen_ids = set()
        users = []
        for channel, info in ACTIVE_USERS.items():
            uid = info['user_id']
            if uid not in seen_ids:
                seen_ids.add(uid)
                users.append({
                    'user_id': uid,
                    'username': info['username'],
                    'avatar': info['avatar'],
                    'ip': info['ip'],
                })
        return users

    @database_sync_to_async
    def get_user_info(self):
        """Fetch display name and avatar for the connected user."""
        try:
            profile = self.user.profile
            avatar = profile.avatar_url
        except Exception:
            avatar = '/static/img/default-avatar.svg'

        display_name = self.user.get_full_name() or self.user.username
        return {
            'display_name': display_name,
            'avatar': avatar,
        }
