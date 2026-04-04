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
    """Extract IP from request headers."""
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
        ip_address=ip,
        defaults={'device_name': request.META.get('HTTP_USER_AGENT', '')[:250]}
    )
    
    # Generate pairing URL (assuming local network operation)
    # The URL needs to point to the endpoint that handles the scan
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
        
    # Standard logic: redirect to start_conversation logic from chat
    # We can redirect directly to the start_conversation route
    return redirect('chat:start_conversation', user_id=device.user.id)

@login_required
def heartbeat(request):
    """Ping endpoint to keep device active and return nearby devices."""
    ip = get_client_ip(request)
    
    # Update current user
    device, created = NearbyDevice.objects.get_or_create(
        user=request.user,
        ip_address=ip,
        defaults={'device_name': request.META.get('HTTP_USER_AGENT', '')[:250]}
    )
    device.save() # Updates last_active
    
    # Find others on same network subnet
    subnet = ip.rsplit('.', 1)[0]
    cutoff = timezone.now() - datetime.timedelta(minutes=5)
    
    active_devices = NearbyDevice.objects.filter(
        ip_address__startswith=subnet,
        last_active__gte=cutoff
    ).exclude(user=request.user)
    
    devices = []
    for d in active_devices:
        profile = getattr(d.user, 'profile', None)
        devices.append({
            'user_id': d.user.id,
            'username': d.user.get_full_name() or d.user.username,
            'avatar': profile.avatar_url if profile else '/static/img/default-avatar.svg',
            'ip': d.ip_address,
            'device_name': d.device_name
        })
        
    return JsonResponse({'devices': devices})
