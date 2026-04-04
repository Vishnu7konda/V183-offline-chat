"""
Accounts — Views
Registration, login, logout, profile, block/unblock, Twilio OTP with rate limiting, JWT token.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth.forms import PasswordChangeForm
from .forms import RegisterForm, LoginForm, ProfileForm
from .models import UserProfile, BlockedUser
import json
import random
import time
import logging
import jwt
import datetime

logger = logging.getLogger(__name__)

# ── OTP Rate Limiting Config ──
OTP_MAX_REQUESTS = 3       # Max OTP requests per window
OTP_WINDOW_SECONDS = 600   # 10-minute window
OTP_EXPIRY_SECONDS = 300   # 5-minute OTP expiry


def register_view(request):
    if request.user.is_authenticated:
        return redirect('chat:chat_home')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, 'Welcome to V-OFFLINE CHAT!')
            return redirect('chat:chat_home')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {
        'form': form,
    })


def login_view(request):
    if request.user.is_authenticated:
        return redirect('chat:chat_home')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            user.profile.is_online = True
            user.profile.save()
            return redirect('chat:chat_home')
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {
        'form': form,
    })


@csrf_exempt
def send_otp_view(request):
    """Send a 6-digit OTP to a phone number via Twilio SMS (with rate limiting)."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid request'})

    phone = data.get('phone', '').strip()
    if not phone or len(phone) < 10:
        return JsonResponse({'status': 'error', 'message': 'Please enter a valid phone number'})

    # ── Rate Limiting ──
    now = time.time()
    window_start = request.session.get('otp_window_start', 0)
    request_count = request.session.get('otp_request_count', 0)

    # Reset window if expired
    if now - window_start > OTP_WINDOW_SECONDS:
        window_start = now
        request_count = 0
        request.session['otp_window_start'] = window_start

    if request_count >= OTP_MAX_REQUESTS:
        remaining = int(OTP_WINDOW_SECONDS - (now - window_start))
        return JsonResponse({
            'status': 'error',
            'message': f'Too many attempts. Please wait {remaining // 60} min {remaining % 60} sec.'
        }, status=429)

    # Increment counter
    request_count += 1
    request.session['otp_request_count'] = request_count
    request.session['otp_window_start'] = window_start

    # Generate a 6-digit OTP
    otp = str(random.randint(100000, 999999))

    # Store in session with expiry timestamp
    request.session['pending_otp'] = otp
    request.session['pending_phone'] = phone
    request.session['otp_created_at'] = now

    # Try sending via Twilio
    twilio_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
    twilio_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
    twilio_service = getattr(settings, 'TWILIO_MESSAGING_SERVICE_SID', '')

    if twilio_sid and twilio_token and twilio_service:
        try:
            from twilio.rest import Client
            client = Client(twilio_sid, twilio_token)
            message = client.messages.create(
                messaging_service_sid=twilio_service,
                to=phone,
                body=f'Your V-OFFLINE CHAT verification code is: {otp}. Valid for 5 minutes.',
            )
            logger.info(f'[Twilio] SMS sent to {phone}, SID: {message.sid}')
            return JsonResponse({'status': 'sent', 'message': f'Code sent to {phone}'})
        except Exception as e:
            logger.error(f'[Twilio] SMS failed: {e}')
            return JsonResponse({'status': 'error', 'message': f'SMS delivery failed: {str(e)}'})
    else:
        # Fallback: print to console for local dev
        logger.info(f'[Nexus OTP] {phone}: {otp}')
        print(f'\n[Nexus OTP] Verification code for {phone}: {otp}\n')
        return JsonResponse({'status': 'sent', 'message': f'Code sent to {phone} (demo mode)'})


@csrf_exempt
def verify_otp_view(request):
    """Verify OTP and log in / create user."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid request'})

    otp = data.get('otp', '').strip()
    phone = data.get('phone', '').strip()

    expected_otp = request.session.get('pending_otp', '')
    expected_phone = request.session.get('pending_phone', '')
    otp_time = request.session.get('otp_created_at', 0)

    # Check expiry (5 minutes)
    if time.time() - otp_time > OTP_EXPIRY_SECONDS:
        return JsonResponse({'status': 'error', 'message': 'Code expired. Please request a new one.'})

    if not otp or otp != expected_otp or phone != expected_phone:
        return JsonResponse({'status': 'error', 'message': 'Invalid verification code'})

    # Find or create user by phone number
    clean_phone = phone.replace('+', '').replace(' ', '').replace('-', '')
    username = f'phone_{clean_phone[-10:]}'

    # Check if user with this phone exists (stored in profile)
    profile = UserProfile.objects.filter(phone_number=phone).first()
    if profile:
        user = profile.user
    else:
        user, created = User.objects.get_or_create(
            username=username,
            defaults={'first_name': f'User {clean_phone[-4:]}'}
        )
        if created:
            user.set_unusable_password()
            user.save()
        # Save phone to profile
        user.profile.phone_number = phone
        user.profile.save()

    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    user.profile.is_online = True
    user.profile.save()

    # Clear session OTP data
    for key in ['pending_otp', 'pending_phone', 'otp_created_at']:
        request.session.pop(key, None)

    return JsonResponse({'status': 'verified', 'redirect': '/chat/'})


@login_required
def logout_view(request):
    request.user.profile.is_online = False
    request.user.profile.save()
    logout(request)
    return redirect('accounts:login')


@login_required
def profile_view(request):
    profile = request.user.profile
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            request.user.first_name = form.cleaned_data.get('first_name', '')
            request.user.last_name = form.cleaned_data.get('last_name', '')
            request.user.save()
            messages.success(request, 'Profile updated!')
            return redirect('accounts:profile')
    else:
        form = ProfileForm(instance=profile, initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
        })
    return render(request, 'accounts/profile.html', {'form': form})


from django.contrib.auth import update_session_auth_hash
@login_required
def password_change_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # Important: keep user logged in after password change
            update_session_auth_hash(request, user)
            messages.success(request, 'Password update successful. Node integrity secured.')
            return redirect('accounts:profile')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'accounts/change_password.html', {'form': form})


@login_required
def user_profile_view(request, username):
    target_user = get_object_or_404(User, username=username)
    is_blocked = BlockedUser.objects.filter(
        blocker=request.user, blocked=target_user
    ).exists()
    return render(request, 'accounts/user_profile.html', {
        'target_user': target_user,
        'is_blocked': is_blocked,
    })


@login_required
def block_user(request, user_id):
    target = get_object_or_404(User, id=user_id)
    BlockedUser.objects.get_or_create(blocker=request.user, blocked=target)
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({'status': 'blocked'})
    return redirect('accounts:user_profile', username=target.username)


@login_required
def unblock_user(request, user_id):
    BlockedUser.objects.filter(blocker=request.user, blocked_id=user_id).delete()
    if request.headers.get('Accept') == 'application/json':
        return JsonResponse({'status': 'unblocked'})
    return redirect('accounts:user_profile', username=User.objects.get(id=user_id).username)


# ── JWT Token ────────────────────────────────────────────────────────────────

def generate_jwt(user):
    """Generate a JWT token for the given user."""
    secret = getattr(settings, 'JWT_SECRET_KEY', settings.SECRET_KEY)
    expiry_hours = getattr(settings, 'JWT_EXPIRY_HOURS', 24)
    payload = {
        'user_id': user.id,
        'username': user.username,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=expiry_hours),
        'iat': datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, secret, algorithm='HS256')


@login_required
def get_jwt_token(request):
    """Return a JWT token for the authenticated user (for WebSocket auth)."""
    token = generate_jwt(request.user)
    return JsonResponse({'token': token})
