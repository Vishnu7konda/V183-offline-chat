import json
import os
import uuid
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q, Max, Count
from django.conf import settings
from django.utils import timezone
from .models import Conversation, Message


@login_required
def chat_home(request):
    qs = Conversation.objects.filter(
        participants=request.user
    )
    # Org-scope filtering
    org = getattr(request, 'organization', None)
    if org:
        qs = qs.filter(organization=org)

    conversations = [c for c in qs.order_by('-updated_at') if not c.is_archived]

    return render(request, 'chat/chat.html', {
        'conversations': conversations,
        'active_conversation': None,
    })


@login_required
def conversation_view(request, conversation_id):
    qs = Conversation.objects.filter(participants=request.user)
    org = getattr(request, 'organization', None)
    if org:
        qs = qs.filter(organization=org)

    conversation = get_object_or_404(qs, id=conversation_id)
    messages_qs = conversation.messages.order_by('timestamp')

    # Mark messages as read
    unseen = messages_qs.filter(is_read=False).exclude(sender=request.user)
    if unseen.exists():
        unseen.update(is_read=True)

    # Get other participant
    other_user = conversation.participants.exclude(id=request.user.id).first()

    conv_qs = Conversation.objects.filter(
        participants=request.user
    )
    if org:
        conv_qs = conv_qs.filter(organization=org)

    conversations = [c for c in conv_qs.order_by('-updated_at') if not c.is_archived]

    return render(request, 'chat/chat.html', {
        'conversations': conversations,
        'active_conversation': conversation,
        'messages': messages_qs,
        'other_user': other_user,
    })


@login_required
def start_conversation(request, user_id):
    other_user = get_object_or_404(User, id=user_id)
    if other_user == request.user:
        return redirect('chat:chat_home')

    org = getattr(request, 'organization', None)

    # Check if conversation already exists
    qs = Conversation.objects.filter(
        participants=request.user
    ).filter(
        participants=other_user
    )
    if org:
        qs = qs.filter(organization=org)
    existing = qs.first()

    if existing:
        return redirect('chat:conversation', conversation_id=existing.id)

    # Create new conversation
    conversation = Conversation.objects.create(organization=org)
    conversation.participants.add(request.user, other_user)

    # System message
    Message.objects.create(
        conversation=conversation,
        sender=request.user,
        content=f'Conversation started with {other_user.username}',
        message_type='system',
    )

    return redirect('chat:conversation', conversation_id=conversation.id)


# ── File Upload Settings ─────────────────────────────────────────────────────
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB


def _validate_upload(uploaded_file):
    """Validate file size and extension. Returns error string or None."""
    if uploaded_file.size > MAX_UPLOAD_SIZE:
        return f'File too large. Maximum size is {MAX_UPLOAD_SIZE // (1024*1024)} MB.'

    ext = os.path.splitext(uploaded_file.name)[1].lower().lstrip('.')
    allowed = getattr(settings, 'ALLOWED_UPLOAD_EXTENSIONS', [])
    if allowed and ext not in allowed:
        return f'File type .{ext} is not allowed.'

    return None


def _unique_filename(original_name):
    """Generate a UUID-prefixed unique filename."""
    ext = os.path.splitext(original_name)[1]
    return f'{uuid.uuid4().hex[:12]}_{original_name}'


@login_required
def upload_media(request, conversation_id):
    """Upload a file via HTTP, save it, broadcast metadata via WebSocket."""
    if request.method != 'POST' or not request.FILES.get('media'):
        return JsonResponse({'error': 'No file provided'}, status=400)

    conversation = get_object_or_404(
        Conversation.objects.filter(participants=request.user),
        id=conversation_id
    )

    uploaded = request.FILES['media']

    # Validate file
    error = _validate_upload(uploaded)
    if error:
        return JsonResponse({'error': error}, status=413)

    # Set unique filename
    uploaded.name = _unique_filename(uploaded.name)

    content_type = uploaded.content_type

    if content_type.startswith('image/'):
        msg_type = 'image'
    elif content_type.startswith('video/'):
        msg_type = 'video'
    elif content_type.startswith('audio/'):
        msg_type = 'voice'
    else:
        msg_type = 'document'

    message = Message.objects.create(
        conversation=conversation,
        sender=request.user,
        content=request.POST.get('caption', uploaded.name),
        message_type=msg_type,
        media=uploaded,
    )

    # Update conversation timestamp
    conversation.updated_at = timezone.now()
    conversation.save(update_fields=['updated_at'])

    return JsonResponse({'message': message.to_json()})


@login_required
def toggle_pin(request, conversation_id):
    conv = get_object_or_404(
        Conversation.objects.filter(participants=request.user),
        id=conversation_id
    )
    conv.is_pinned = not conv.is_pinned
    conv.save(update_fields=['is_pinned'])
    return JsonResponse({'is_pinned': conv.is_pinned})


@login_required
def toggle_archive(request, conversation_id):
    conv = get_object_or_404(
        Conversation.objects.filter(participants=request.user),
        id=conversation_id
    )
    conv.is_archived = not conv.is_archived
    conv.save(update_fields=['is_archived'])
    return JsonResponse({'is_archived': conv.is_archived})


@login_required
def search_messages(request):
    query = request.GET.get('q', '').strip()
    results = []
    if query:
        results = Message.objects.filter(
            conversation__participants=request.user,
            content__icontains=query,
            is_deleted=False,
        ).order_by('-timestamp')[:30]
    if request.headers.get('Accept') == 'application/json':
        data = [msg.to_json() for msg in results]
        return JsonResponse({'messages': data})
    return render(request, 'chat/search.html', {'results': results, 'query': query})


@login_required
def archived_chats(request):
    conversations = Conversation.objects.filter(
        participants=request.user,
        is_archived=True
    ).annotate(
        last_msg_time=Max('messages__timestamp')
    ).order_by('-last_msg_time')
    return render(request, 'chat/archived.html', {'conversations': conversations})


import json
@login_required
def create_group(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)
    
    try:
        data = json.loads(request.body)
        name = data.get('name')
        participant_ids = data.get('participants', [])
        
        if not name:
            return JsonResponse({'error': 'Name required'}, status=400)
        
        org = getattr(request, 'organization', None)
        conversation = Conversation.objects.create(
            organization=org,
            is_group=True,
            group_name=name
        )
        
        # Add creator and participants
        participants = User.objects.filter(id__in=participant_ids)
        conversation.participants.add(request.user, *participants)
        
        # System message
        Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=f'Team Node "{name}" initialized by {request.user.username}',
            message_type='system',
        )
        
        return JsonResponse({'id': conversation.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ── HTTP Message API (Vercel-compatible, replaces WebSocket send) ───────────────

@login_required
@require_POST
def send_message(request, conversation_id):
    """Send a text message via HTTP POST. Replaces WebSocket send on Vercel."""
    conversation = get_object_or_404(
        Conversation.objects.filter(participants=request.user),
        id=conversation_id
    )
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    content = (data.get('content') or '').strip()
    if not content:
        return JsonResponse({'error': 'Empty message'}, status=400)

    message = Message.objects.create(
        conversation=conversation,
        sender=request.user,
        content=content,
        message_type='text',
    )
    conversation.updated_at = timezone.now()
    conversation.save(update_fields=['updated_at'])

    return JsonResponse({'message': message.to_json()}, status=201)


@login_required
def poll_messages(request, conversation_id):
    """Return messages newer than `after` message id. Used for HTTP polling."""
    conversation = get_object_or_404(
        Conversation.objects.filter(participants=request.user),
        id=conversation_id
    )
    after_id = request.GET.get('after', 0)
    try:
        after_id = int(after_id)
    except (TypeError, ValueError):
        after_id = 0

    base_qs = conversation.messages.filter(
        id__gt=after_id
    ).order_by('timestamp')

    # Mark as read using the unsliced queryset (sliced QS can't be filtered)
    base_qs.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

    # Now slice for the response payload
    messages = list(base_qs.select_related('sender')[:50])

    return JsonResponse({
        'messages': [m.to_json() for m in messages]
    })
