from django.urls import path
from . import views

app_name = 'organizations'

urlpatterns = [
    path('register/', views.register_org, name='register_org'),
    path('select/', views.select_org, name='select_org'),
    path('join/<uuid:invite_code>/', views.join_org, name='join_org'),
    path('switch/<int:org_id>/', views.switch_org, name='switch_org'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('settings/', views.org_settings, name='settings'),
    path('members/', views.manage_members, name='members'),
    path('invite/', views.send_invitation, name='send_invitation'),
    path('api/stats/', views.api_dashboard_stats, name='api_stats'),
]
