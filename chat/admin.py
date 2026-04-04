from django.contrib import admin
from .models import Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'updated_at', 'is_pinned', 'is_archived')
    list_filter = ('is_pinned', 'is_archived')
    filter_horizontal = ('participants',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'conversation', 'message_type', 'timestamp', 'is_read', 'is_deleted')
    list_filter = ('message_type', 'is_read', 'is_delivered', 'is_deleted')
    search_fields = ('content', 'sender__username')
    raw_id_fields = ('sender', 'conversation', 'reply_to')
