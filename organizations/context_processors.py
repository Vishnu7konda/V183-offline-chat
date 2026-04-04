"""
Organizations — Context Processors
Injects organization and branding variables into all templates.
"""


def organization_context(request):
    """Add organization data and branding to template context."""
    org = getattr(request, 'organization', None)
    ctx = {
        'current_org': org,
        'org_name': org.app_name if org else 'V-OFFLINE CHAT',
        'org_logo': org.logo_url if org else '/static/img/default-avatar.svg',
        'org_primary_color': org.primary_color if org else '#6C5CE7',
        'org_secondary_color': org.secondary_color if org else '#a29bfe',
        'org_nearby_enabled': org.nearby_mode_enabled if org else True,
        'org_file_sharing': org.file_sharing_enabled if org else True,
    }

    # Get user's org list for org switcher
    if hasattr(request, 'user') and request.user.is_authenticated:
        from organizations.models import OrganizationMembership
        ctx['user_organizations'] = OrganizationMembership.objects.filter(
            user=request.user, is_active=True
        )[:10]

    return ctx
