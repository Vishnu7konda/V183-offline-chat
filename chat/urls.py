"""
Chat — URL Configuration
"""
from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    path('', views.chat_home, name='chat_home'),
    path('<int:conversation_id>/', views.conversation_view, name='conversation'),
    path('start/<int:user_id>/', views.start_conversation, name='start_conversation'),
    path('<int:conversation_id>/upload/', views.upload_media, name='upload_media'),
    path('<int:conversation_id>/pin/', views.toggle_pin, name='toggle_pin'),
    path('<int:conversation_id>/archive/', views.toggle_archive, name='toggle_archive'),
    path('search/', views.search_messages, name='search_messages'),
    path('archived/', views.archived_chats, name='archived_chats'),
    path('group/create/', views.create_group, name='create_group'),
]
