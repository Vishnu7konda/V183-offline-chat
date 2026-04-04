from django.db import models
from django.contrib.auth.models import User
import uuid

class NearbyDevice(models.Model):
    organization = models.ForeignKey(
        'organizations.Organization', on_delete=models.CASCADE,
        related_name='nearby_devices', null=True, blank=True
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='nearby_devices')
    ip_address = models.GenericIPAddressField()
    device_name = models.CharField(max_length=255, blank=True, null=True)
    last_active = models.DateTimeField(auto_now=True)
    pairing_code = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    class Meta:
        unique_together = ('user', 'ip_address')
        ordering = ['-last_active']
        
    def __str__(self):
        return f"{self.user.username} - {self.ip_address}"
