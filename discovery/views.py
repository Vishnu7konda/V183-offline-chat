import qrcode
import base64
from io import BytesIO
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from .models import NearbyDevice
from accounts.models import UserProfile
import datetime

def get_client_ip(request):
    """Extract IP from request headers — handles Vercel/proxy forwarding."""
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


@login_required
def generate_qr(request):
    """Generate a QR code for the current user's nearby connection."""
    ip = get_client_ip(request)
    device, created = NearbyDevice.objects.get_or_create(
        user=request.user,
        defaults={
            'ip_address': ip,
            'device_name': request.META.get('HTTP_USER_AGENT', '')[:250]
        }
    )
    if not created:
        device.ip_address = ip
        device.device_name = request.META.get('HTTP_USER_AGENT', '')[:250]
        device.save()

    host = request.get_host()
    scheme = request.scheme
    pairing_url = f"{scheme}://{host}/discovery/pair/{device.pairing_code}/"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(pairing_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    img_str = base64.b64encode(buffer.getvalue()).decode()

    return JsonResponse({'qr_image': f"data:image/png;base64,{img_str}"})


@login_required
def scan_pair(request, pairing_code):
    """Handle QR code scan by another user to initiate chat."""
    device = get_object_or_404(NearbyDevice, pairing_code=pairing_code)

    if device.user == request.user:
        return redirect('chat:chat_home')

    return redirect('chat:start_conversation', user_id=device.user.id)


@login_required
def heartbeat(request):
    """
    Ping endpoint — keeps device active and returns all recently-active users.

    Cloud-mode: Because Vercel proxies all traffic through shared IPs,
    we can no longer rely on IP-subnet matching. Instead we show ALL
    users who have been active in the last 5 minutes (regardless of IP),
    so devices on different networks can still discover each other.
    """
    ip = get_client_ip(request)

    # Upsert: one NearbyDevice row per user (remove unique_together on ip)
    try:
        device = NearbyDevice.objects.get(user=request.user)
        device.ip_address = ip
        device.device_name = request.META.get('HTTP_USER_AGENT', '')[:250]
        device.save()
    except NearbyDevice.DoesNotExist:
        device = NearbyDevice.objects.create(
            user=request.user,
            ip_address=ip,
            device_name=request.META.get('HTTP_USER_AGENT', '')[:250]
        )

    cutoff = timezone.now() - datetime.timedelta(minutes=5)

    # ── Cloud-friendly: show ALL recently-active users except self ──
    # Also filter by same organization if the user belongs to one, so
    # users from different orgs don't see each other.
    user_profile = getattr(request.user, 'profile', None)
    active_org = getattr(user_profile, 'active_organization', None)

    qs = NearbyDevice.objects.filter(
        last_active__gte=cutoff
    ).exclude(user=request.user).select_related('user')

    # If user has an org, only show members of that org
    if active_org:
        org_user_ids = active_org.memberships.values_list('user_id', flat=True)
        qs = qs.filter(user_id__in=org_user_ids)

    devices = []
    for d in qs:
        profile = getattr(d.user, 'profile', None)
        devices.append({
            'user_id': d.user.id,
            'username': d.user.get_full_name() or d.user.username,
            'avatar': profile.avatar_url if profile else '/static/img/default-avatar.svg',
            'ip': d.ip_address,
            'device_name': d.device_name,
        })

    return JsonResponse({'devices': devices})
