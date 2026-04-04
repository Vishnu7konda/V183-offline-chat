"""
Chat — WebSocket Consumers
Async consumer for real-time messaging over WebSockets.
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class ChatConsumer(AsyncWebsocketConsumer):
    """
    Handles WebSocket connections for chat conversations.
    Supports: messages, typing indicators, read receipts, reactions,
    edit/delete, and online presence.
    """

    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        self.user = self.scope['user']

        if self.user.is_anonymous:
            await self.close()
            return

        # Verify user is a participant in this conversation
        is_participant = await self.check_participant()
        if not is_participant:
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        # Set user online
        await self.set_online(True)

        # Notify group that user is online
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'username': self.user.username,
                'is_online': True,
            }
        )

    async def disconnect(self, close_code):
        await self.set_online(False)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_status',
                'username': self.user.username,
                'is_online': False,
            }
        )
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type', 'message')

        if msg_type == 'message':
            message = await self.save_message(data.get('content', ''))
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                }
            )
        elif msg_type == 'typing':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_indicator',
                    'username': self.user.username,
                    'is_typing': data.get('is_typing', False),
                }
            )
        elif msg_type == 'read_receipt':
            message_id = data.get('message_id')
            # Handle global (all) or specific message read
            await self.mark_as_read(message_id)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'read_receipt',
                    'message_id': message_id,
                    'reader': self.user.username,
                }
            )
        elif msg_type == 'delivery_receipt':
            message_id = data.get('message_id')
            # Set message as delivered in DB
            await self.mark_as_delivered(message_id)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'delivery_receipt',
                    'message_id': message_id,
                    'username': self.user.username,
                }
            )
        elif msg_type == 'reaction':
            message_id = data.get('message_id')
            emoji = data.get('emoji')
            if message_id and emoji:
                await self.add_reaction(message_id, emoji)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'message_reaction',
                        'message_id': message_id,
                        'emoji': emoji,
                        'username': self.user.username,
                    }
                )
        elif msg_type == 'edit':
            message_id = data.get('message_id')
            new_content = data.get('content', '')
            if message_id:
                await self.edit_message(message_id, new_content)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'message_edited',
                        'message_id': message_id,
                        'content': new_content,
                        'username': self.user.username,
                    }
                )
        elif msg_type == 'delete':
            message_id = data.get('message_id')
            if message_id:
                await self.delete_message(message_id)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'message_deleted',
                        'message_id': message_id,
                        'username': self.user.username,
                    }
                )

    # ── Group message handlers ──────────────────────────────────────────

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': event['message'],
        }))

    async def typing_indicator(self, event):
        if event['username'] != self.user.username:
            await self.send(text_data=json.dumps({
                'type': 'typing',
                'username': event['username'],
                'is_typing': event['is_typing'],
            }))

    async def read_receipt(self, event):
        await self.send(text_data=json.dumps({
            'type': 'read_receipt',
            'message_id': event['message_id'],
            'reader': event['reader'],
        }))

    async def message_reaction(self, event):
        await self.send(text_data=json.dumps({
            'type': 'reaction',
            'message_id': event['message_id'],
            'emoji': event['emoji'],
            'username': event['username'],
        }))

    async def message_edited(self, event):
        await self.send(text_data=json.dumps({
            'type': 'edited',
            'message_id': event['message_id'],
            'content': event['content'],
        }))

    async def message_deleted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'deleted',
            'message_id': event['message_id'],
        }))

    async def user_status(self, event):
        await self.send(text_data=json.dumps({
            'type': 'status',
            'username': event['username'],
            'is_online': event['is_online'],
        }))

    # ── Database operations ──────────────────────────────────────────────

    @database_sync_to_async
    def save_message(self, content):
        from chat.models import Conversation, Message
        conv = Conversation.objects.get(id=self.conversation_id)
        msg = Message.objects.create(
            conversation=conv,
            sender=self.user,
            content=content,
        )
        conv.updated_at = timezone.now()
        conv.save(update_fields=['updated_at'])
        return msg.to_json()

    @database_sync_to_async
    def mark_as_read(self, message_id=None):
        from chat.models import Message
        queryset = Message.objects.filter(
            conversation_id=self.conversation_id,
            is_read=False
        ).exclude(sender=self.user)
        
        if message_id:
            queryset = queryset.filter(id=message_id)
        
        queryset.update(is_read=True)
        return True

    @database_sync_to_async
    def mark_as_delivered(self, message_id=None):
        from chat.models import Message
        queryset = Message.objects.filter(
            conversation_id=self.conversation_id,
            is_delivered=False
        ).exclude(sender=self.user)
        
        if message_id:
            queryset = queryset.filter(id=message_id)
        
        queryset.update(is_delivered=True)
        return True

    @database_sync_to_async
    def add_reaction(self, message_id, emoji):
        from chat.models import Message
        try:
            msg = Message.objects.get(id=message_id, conversation_id=self.conversation_id)
            reactions = msg.reactions or {}
            username = self.user.username
            if emoji in reactions:
                if username in reactions[emoji]:
                    reactions[emoji].remove(username)
                    if not reactions[emoji]:
                        del reactions[emoji]
                else:
                    reactions[emoji].append(username)
            else:
                reactions[emoji] = [username]
            msg.reactions = reactions
            msg.save(update_fields=['reactions'])
        except Exception:
            pass

    @database_sync_to_async
    def edit_message(self, message_id, new_content):
        from chat.models import Message
        Message.objects.filter(
            id=message_id,
            sender=self.user,
            conversation_id=self.conversation_id
        ).update(content=new_content, is_edited=True)

    @database_sync_to_async
    def delete_message(self, message_id):
        from chat.models import Message
        Message.objects.filter(
            id=message_id,
            sender=self.user,
            conversation_id=self.conversation_id
        ).update(is_deleted=True, content='')

    @database_sync_to_async
    def set_online(self, status):
        try:
            profile = self.user.profile
            profile.is_online = status
            if not status:
                profile.last_seen = timezone.now()
            profile.save(update_fields=['is_online', 'last_seen'])
        except Exception:
            pass

    @database_sync_to_async
    def check_participant(self):
        """Verify the user is a participant in the conversation."""
        from chat.models import Conversation
        return Conversation.objects.filter(
            id=self.conversation_id,
            participants=self.user
        ).exists()
