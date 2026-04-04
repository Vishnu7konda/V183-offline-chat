"""
Organizations — Models
Multi-tenant architecture: Organization, Membership, Invitation, AuditLog, SubscriptionPlan.
"""
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class SubscriptionPlan(models.Model):
    """Defines feature tiers: Free, Pro, Enterprise."""
    TIER_CHOICES = [
        ('free', 'Free'),
        ('pro', 'Pro'),
        ('enterprise', 'Enterprise'),
    ]
    name = models.CharField(max_length=100)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='free', unique=True)
    max_users = models.PositiveIntegerField(default=25)
    max_storage_mb = models.PositiveIntegerField(default=500)
    features = models.JSONField(default=dict, blank=True, help_text='Feature flags JSON')
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_yearly = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.tier})"

    class Meta:
        ordering = ['price_monthly']


class Organization(models.Model):
    """A tenant workspace — company, college, or team."""
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=100, unique=True, help_text='Unique org code / subdomain')
    logo = models.ImageField(upload_to='org_logos/', blank=True, null=True)
    description = models.TextField(blank=True, default='')

    # Branding
    primary_color = models.CharField(max_length=7, default='#6C5CE7', help_text='Hex color')
    secondary_color = models.CharField(max_length=7, default='#a29bfe')
    app_name = models.CharField(max_length=100, default='V-OFFLINE CHAT', help_text='Custom app title')

    # Subscription & limits
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_demo = models.BooleanField(default=False, help_text='Demo org for presentations')

    # Feature toggles
    nearby_mode_enabled = models.BooleanField(default=True)
    file_sharing_enabled = models.BooleanField(default=True)
    max_file_size_mb = models.PositiveIntegerField(default=10)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_orgs')

    def __str__(self):
        return self.name

    @property
    def logo_url(self):
        if self.logo and hasattr(self.logo, 'url'):
            return self.logo.url
        return '/static/img/default-avatar.svg'

    @property
    def member_count(self):
        return self.memberships.filter(is_active=True).count()

    class Meta:
        ordering = ['name']


class OrganizationMembership(models.Model):
    """Links users to organizations with role-based access."""
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('moderator', 'Moderator'),
        ('member', 'Member'),
    ]
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='org_memberships')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    is_active = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} → {self.organization.name} ({self.role})"

    @property
    def is_admin_or_above(self):
        return self.role in ('owner', 'admin')

    class Meta:
        unique_together = ('organization', 'user')
        ordering = ['-joined_at']


class Invitation(models.Model):
    """Email/link-based invitations to join an organization."""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='invitations')
    email = models.EmailField()
    invite_code = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    role = models.CharField(max_length=20, choices=OrganizationMembership.ROLE_CHOICES, default='member')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    accepted = models.BooleanField(default=False)
    accepted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='accepted_invitations')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Invite to {self.organization.name} for {self.email}"

    @property
    def is_expired(self):
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False

    class Meta:
        ordering = ['-created_at']


class AuditLog(models.Model):
    """Tracks important actions within an organization."""
    ACTION_CHOICES = [
        ('user_joined', 'User Joined'),
        ('user_removed', 'User Removed'),
        ('role_changed', 'Role Changed'),
        ('settings_updated', 'Settings Updated'),
        ('invitation_sent', 'Invitation Sent'),
        ('login', 'Login'),
        ('message_deleted', 'Message Deleted'),
        ('file_uploaded', 'File Uploaded'),
        ('org_created', 'Organization Created'),
    ]
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='audit_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.organization.slug}] {self.action} by {self.user}"

    class Meta:
        ordering = ['-timestamp']
