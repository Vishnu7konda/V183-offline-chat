"""
Organizations — Middleware
Resolves the active organization from session and attaches it to the request.
"""
from django.shortcuts import redirect
from django.urls import reverse


class OrganizationMiddleware:
    """Attaches request.organization from session for tenant-scoped queries."""

    EXEMPT_PATHS = [
        '/accounts/login/',
        '/accounts/register/',
        '/accounts/logout/',
        '/admin/',
        '/static/',
        '/media/',
        '/org/select/',
        '/org/register/',
        '/org/join/',
        '/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.organization = None

        if request.user.is_authenticated:
            org_id = request.session.get('active_org_id')
            if org_id:
                from organizations.models import Organization, OrganizationMembership
                try:
                    org = Organization.objects.get(id=org_id, is_active=True)
                    # Verify user is a member
                    mem = OrganizationMembership.objects.filter(organization=org, user=request.user).first()
                    if mem and mem.is_active:
                        request.organization = org
                except Organization.DoesNotExist:
                    del request.session['active_org_id']

            # If no org set and user has memberships, auto-set the first one
            if not request.organization:
                from organizations.models import OrganizationMembership
                memberships = OrganizationMembership.objects.filter(user=request.user)
                membership = next((m for m in memberships if m.is_active), None)
                if membership:
                    request.organization = membership.organization
                    request.session['active_org_id'] = membership.organization.id

        response = self.get_response(request)
        return response
