"""
Organizations — Decorators
Permission decorators for organization-scoped views.
"""
from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import redirect


def org_member_required(view_func):
    """Ensure user belongs to the active organization."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not getattr(request, 'organization', None):
            return redirect('organizations:select_org')
        return view_func(request, *args, **kwargs)
    return wrapper


def org_admin_required(view_func):
    """Ensure user is admin or owner of the active organization."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        org = getattr(request, 'organization', None)
        if not org:
            return redirect('organizations:select_org')

        from organizations.models import OrganizationMembership
        membership = OrganizationMembership.objects.filter(
            organization=org, user=request.user, is_active=True
        ).first()

        if not membership or not membership.is_admin_or_above:
            return HttpResponseForbidden('You do not have admin access to this organization.')

        request.org_membership = membership
        return view_func(request, *args, **kwargs)
    return wrapper
