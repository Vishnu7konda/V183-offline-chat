"""
Organizations — Views
Org registration, selection, settings, invitations, admin dashboard.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.utils.text import slugify
from django.utils import timezone
from django.db.models import Count, Sum, Q
from .models import Organization, OrganizationMembership, Invitation, AuditLog, SubscriptionPlan
from .decorators import org_admin_required, org_member_required
import datetime


def register_org(request):
    """Register a new organization workspace."""
    if request.method == 'POST':
        name = request.POST.get('org_name', '').strip()
        slug = request.POST.get('org_slug', '').strip() or slugify(name)
        description = request.POST.get('description', '')

        if not name:
            messages.error(request, 'Organization name is required.')
            return render(request, 'organizations/register.html')

        if Organization.objects.filter(slug=slug).exists():
            messages.error(request, 'This organization code is already taken.')
            return render(request, 'organizations/register.html')

        org = Organization.objects.create(
            name=name,
            slug=slug,
            description=description,
            created_by=request.user if request.user.is_authenticated else None,
        )

        # Handle logo upload
        if request.FILES.get('logo'):
            org.logo = request.FILES['logo']
            org.save()

        # If user is logged in, make them owner
        if request.user.is_authenticated:
            OrganizationMembership.objects.create(
                organization=org, user=request.user, role='owner'
            )
            request.session['active_org_id'] = org.id
            AuditLog.objects.create(
                organization=org, user=request.user,
                action='org_created', details={'name': name}
            )
            messages.success(request, f'Organization "{name}" created successfully!')
            return redirect('organizations:dashboard')

        messages.success(request, f'Organization "{name}" created! Please register an account.')
        return redirect('accounts:register')

    return render(request, 'organizations/register.html')


@login_required
def select_org(request):
    """Let user pick their active organization."""
    memberships = OrganizationMembership.objects.filter(
        user=request.user, is_active=True
    )

    if request.method == 'POST':
        org_id = request.POST.get('org_id')
        if org_id:
            membership = memberships.filter(organization_id=org_id).first()
            if membership:
                request.session['active_org_id'] = int(org_id)
                return redirect('chat:chat_home')

    # Auto-redirect if only one org
    if memberships.count() == 1:
        request.session['active_org_id'] = memberships.first().organization.id
        return redirect('chat:chat_home')

    return render(request, 'organizations/select.html', {'memberships': memberships})


@login_required
def join_org(request, invite_code):
    """Accept an invitation to join an organization."""
    invitation = get_object_or_404(Invitation, invite_code=invite_code, accepted=False)

    if invitation.is_expired:
        messages.error(request, 'This invitation has expired.')
        return redirect('organizations:select_org')

    # Create membership
    membership, created = OrganizationMembership.objects.get_or_create(
        organization=invitation.organization,
        user=request.user,
        defaults={'role': invitation.role}
    )

    if created:
        invitation.accepted = True
        invitation.accepted_by = request.user
        invitation.save()
        AuditLog.objects.create(
            organization=invitation.organization, user=request.user,
            action='user_joined', details={'via': 'invitation', 'role': invitation.role}
        )
        messages.success(request, f'Welcome to {invitation.organization.name}!')
    else:
        messages.info(request, 'You are already a member of this organization.')

    request.session['active_org_id'] = invitation.organization.id
    return redirect('chat:chat_home')


@org_admin_required
def dashboard(request):
    """Organization admin dashboard with analytics."""
    org = request.organization
    now = timezone.now()
    thirty_days_ago = now - datetime.timedelta(days=30)
    seven_days_ago = now - datetime.timedelta(days=7)

    from chat.models import Conversation, Message

    # Core stats
    total_members = org.memberships.filter(is_active=True).count()
    total_conversations = Conversation.objects.filter(organization=org).count()
    total_messages = Message.objects.filter(conversation__organization=org).count()
    messages_this_week = Message.objects.filter(
        conversation__organization=org, timestamp__gte=seven_days_ago
    ).count()

    # Recent members
    recent_members = org.memberships.filter(is_active=True).order_by('-joined_at')[:10]

    # Pending invitations
    pending_invites = org.invitations.filter(accepted=False).order_by('-created_at')[:10]

    # Recent audit logs
    recent_logs = org.audit_logs.order_by('-timestamp')[:20]

    # Messages per day (last 7 days) for chart
    daily_messages = []
    for i in range(7):
        day = now - datetime.timedelta(days=6 - i)
        count = Message.objects.filter(
            conversation__organization=org,
            timestamp__date=day.date()
        ).count()
        daily_messages.append({'date': day.strftime('%a'), 'count': count})

    context = {
        'total_members': total_members,
        'total_conversations': total_conversations,
        'total_messages': total_messages,
        'messages_this_week': messages_this_week,
        'recent_members': recent_members,
        'pending_invites': pending_invites,
        'recent_logs': recent_logs,
        'daily_messages': daily_messages,
    }
    return render(request, 'organizations/dashboard.html', context)


@org_admin_required
def org_settings(request):
    """Organization settings page — branding, features, plan."""
    org = request.organization

    if request.method == 'POST':
        org.name = request.POST.get('name', org.name)
        org.app_name = request.POST.get('app_name', org.app_name)
        org.description = request.POST.get('description', org.description)
        org.primary_color = request.POST.get('primary_color', org.primary_color)
        org.secondary_color = request.POST.get('secondary_color', org.secondary_color)
        org.nearby_mode_enabled = request.POST.get('nearby_mode_enabled') == 'on'
        org.file_sharing_enabled = request.POST.get('file_sharing_enabled') == 'on'
        org.max_file_size_mb = int(request.POST.get('max_file_size_mb', 10))

        if request.FILES.get('logo'):
            org.logo = request.FILES['logo']

        org.save()
        AuditLog.objects.create(
            organization=org, user=request.user,
            action='settings_updated', details={'updated_by': request.user.username}
        )
        messages.success(request, 'Organization settings updated!')
        return redirect('organizations:settings')

    return render(request, 'organizations/settings.html', {'org': org})


@org_admin_required
def manage_members(request):
    """View and manage organization members."""
    org = request.organization
    members = org.memberships.filter(is_active=True)

    if request.method == 'POST':
        action = request.POST.get('action')
        user_id = request.POST.get('user_id')

        if action == 'change_role':
            new_role = request.POST.get('role', 'member')
            membership = get_object_or_404(OrganizationMembership, organization=org, user_id=user_id)
            membership.role = new_role
            membership.save()
            AuditLog.objects.create(
                organization=org, user=request.user,
                action='role_changed',
                details={'target_user': user_id, 'new_role': new_role}
            )
            messages.success(request, 'Role updated.')

        elif action == 'remove':
            membership = get_object_or_404(OrganizationMembership, organization=org, user_id=user_id)
            membership.is_active = False
            membership.save()
            AuditLog.objects.create(
                organization=org, user=request.user,
                action='user_removed', details={'removed_user': user_id}
            )
            messages.success(request, 'Member removed.')

        return redirect('organizations:members')

    return render(request, 'organizations/members.html', {'members': members})


@org_admin_required
def send_invitation(request):
    """Send an invitation email/link."""
    org = request.organization

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        role = request.POST.get('role', 'member')

        if not email:
            messages.error(request, 'Email is required.')
            return redirect('organizations:members')

        invitation = Invitation.objects.create(
            organization=org, email=email, role=role,
            created_by=request.user,
            expires_at=timezone.now() + datetime.timedelta(days=7),
        )
        AuditLog.objects.create(
            organization=org, user=request.user,
            action='invitation_sent', details={'email': email, 'role': role}
        )
        invite_url = request.build_absolute_uri(f'/org/join/{invitation.invite_code}/')
        messages.success(request, f'Invitation link: {invite_url}')
        return redirect('organizations:members')

    return redirect('organizations:members')


@login_required
def switch_org(request, org_id):
    """Switch active organization."""
    membership = get_object_or_404(
        OrganizationMembership,
        organization_id=org_id, user=request.user, is_active=True
    )
    request.session['active_org_id'] = org_id
    return redirect('chat:chat_home')


# ── API endpoints for dashboard charts ──
@org_admin_required
def api_dashboard_stats(request):
    """Return JSON stats for dashboard charts."""
    org = request.organization
    now = timezone.now()

    from chat.models import Message

    daily_messages = []
    for i in range(30):
        day = now - datetime.timedelta(days=29 - i)
        count = Message.objects.filter(
            conversation__organization=org,
            timestamp__date=day.date()
        ).count()
        daily_messages.append({'date': day.strftime('%b %d'), 'count': count})

    return JsonResponse({
        'daily_messages': daily_messages,
        'total_members': org.memberships.filter(is_active=True).count(),
    })
