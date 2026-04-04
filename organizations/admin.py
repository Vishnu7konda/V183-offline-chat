from django.contrib import admin
from .models import Organization, OrganizationMembership, Invitation, AuditLog, SubscriptionPlan


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'plan', 'is_active', 'member_count', 'created_at')
    list_filter = ('is_active', 'plan', 'nearby_mode_enabled')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(OrganizationMembership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization', 'role', 'is_active', 'joined_at')
    list_filter = ('role', 'is_active')
    search_fields = ('user__username', 'organization__name')


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ('email', 'organization', 'role', 'accepted', 'created_at')
    list_filter = ('accepted', 'role')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('organization', 'user', 'action', 'timestamp')
    list_filter = ('action',)
    readonly_fields = ('organization', 'user', 'action', 'details', 'ip_address', 'timestamp')


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'tier', 'max_users', 'max_storage_mb', 'price_monthly', 'is_active')
