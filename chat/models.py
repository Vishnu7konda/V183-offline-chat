"""
Chat — Models
Conversation and Message models for the chat system.
"""
from django.db import models
from django.contrib.auth.models import User


class Conversation(models.Model):
    organization = models.ForeignKey(
        'organizations.Organization', on_delete=models.CASCADE,
        related_name='conversations', null=True, blank=True
    )
    participants = models.ManyToManyField(User, related_name='conversations')
    is_group = models.BooleanField(default=False)
    group_name = models.CharField(max_length=255, blank=True, null=True)
    group_avatar = models.ImageField(upload_to='group_avatars/', blank=True, null=True)
    group_description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_pinned = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        if self.is_group and self.group_name:
            return f'Group: {self.group_name}'
        names = ', '.join(u.username for u in self.participants.all()[:3])
        return f'Chat: {names}'

    @property
    def last_message(self):
        return self.messages.order_by('-timestamp').first()

    def unread_count(self, user):
        return self.messages.filter(is_read=False).exclude(sender=user).count()


class Message(models.Model):
    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('document', 'Document'),
        ('voice', 'Voice Note'),
        ('system', 'System'),
    ]

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name='messages'
    )
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='sent_messages'
    )
    content = models.TextField(blank=True, default='')
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES, default='text')
    media = models.FileField(upload_to='chat_media/%Y/%m/', blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_delivered = models.BooleanField(default=False)
    is_read = models.BooleanField(default=False)
    is_edited = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    reply_to = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='replies'
    )
    reactions = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        preview = self.content[:50] if self.content else f'[{self.message_type}]'
        return f'{self.sender.username}: {preview}'

    def to_json(self):
        return {
            'id': self.id,
            'sender': self.sender.username,
            'sender_id': self.sender.id,
            'sender_avatar': self.sender.profile.avatar_url,
            'content': '' if self.is_deleted else self.content,
            'message_type': self.message_type,
            'media_url': self.media.url if self.media else None,
            'timestamp': self.timestamp.isoformat(),
            'is_delivered': self.is_delivered,
            'is_read': self.is_read,
            'is_edited': self.is_edited,
            'is_deleted': self.is_deleted,
            'reply_to': self.reply_to_id,
            'reactions': self.reactions,
        }
