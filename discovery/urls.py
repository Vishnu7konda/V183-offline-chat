from django.urls import path
from . import views

app_name = 'discovery'

urlpatterns = [
    path('qr/', views.generate_qr, name='generate_qr'),
    path('pair/<uuid:pairing_code>/', views.scan_pair, name='scan_pair'),
    path('heartbeat/', views.heartbeat, name='heartbeat'),
]
