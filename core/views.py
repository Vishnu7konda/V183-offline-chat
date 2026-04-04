"""
Core — Views
Landing page and admin dashboard.
"""
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.db.models import Count
from chat.models import Conversation, Message


def landing_page(request):
    if request.user.is_authenticated:
        return redirect('chat:chat_home')
    return render(request, 'core/landing.html')


@staff_member_required
def admin_dashboard(request):
    stats = {
        'total_users': User.objects.count(),
        'online_users': User.objects.filter(profile__is_online=True).count(),
        'total_conversations': Conversation.objects.count(),
        'total_messages': Message.objects.count(),
        'recent_users': User.objects.order_by('-date_joined')[:10],
    }
    return render(request, 'core/admin_dashboard.html', stats)
