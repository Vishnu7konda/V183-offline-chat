"""
API — Serializers
DRF serializers for Users, Profiles, Conversations, and Messages.
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from accounts.models import UserProfile
from chat.models import Conversation, Message


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['avatar', 'bio', 'is_online', 'last_seen', 'theme']


class UserSerializer(serializers.ModelSerializer):
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'profile']


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.username', read_only=True)
    sender_avatar = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'sender', 'sender_name', 'sender_avatar',
            'content', 'message_type', 'media', 'timestamp',
            'is_delivered', 'is_read', 'is_edited', 'is_deleted',
            'reply_to', 'reactions',
        ]
        read_only_fields = ['sender', 'timestamp']

    def get_sender_avatar(self, obj):
        return obj.sender.profile.avatar_url


class ConversationSerializer(serializers.ModelSerializer):
    participants = UserSerializer(many=True, read_only=True)
    last_message = MessageSerializer(read_only=True)
    unread = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id', 'participants', 'created_at', 'updated_at',
            'is_pinned', 'is_archived', 'last_message', 'unread',
        ]

    def get_unread(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.unread_count(request.user)
        return 0
