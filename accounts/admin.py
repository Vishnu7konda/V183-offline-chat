from django.contrib import admin
from .models import UserProfile, BlockedUser


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_online', 'last_seen', 'theme')
    list_filter = ('is_online', 'theme')
    search_fields = ('user__username', 'user__email')


@admin.register(BlockedUser)
class BlockedUserAdmin(admin.ModelAdmin):
    list_display = ('blocker', 'blocked', 'created_at')
