# Create your models here.

from django.db import models
from django.contrib.auth.models import User

OFFICER_CHOICES = [
    ('CHAIRMAN', 'සභාපති'),
    ('SECRETARY', 'ලේකම්'),
    ('CMO', 'ප්‍රධාන කළමණාකරන නිළධාරී'),
    ('HOD', 'අංශ ප්‍රධානී'),
]

SECTOR_CHOICES = [
    ('GOVERNING', 'Governing'),
    ('HEALTH', 'Health'),
    ('DEVELOPMENT', 'Development'),
    ('INCOME', 'Income'),
    ('ACCOUNTS', 'Accounts'),
]

class Letter(models.Model):
    """The blueprint for every incoming letter"""

    serial_number = models.CharField(max_length=10, unique=True, verbose_name="අනු අංකය", primary_key=True)
    date_received = models.DateField()
    sender_name = models.CharField(max_length=200)
    sender_address = models.TextField()
    letter_type = models.CharField(max_length=200)
    accepting_officer_id = models.CharField(max_length=50)
    target_sector = models.CharField(max_length=20, choices=SECTOR_CHOICES)
    administrated_by = models.CharField(max_length=20, choices=OFFICER_CHOICES)
    is_replied = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    replied_at = models.DateTimeField(null=True, blank=True)\


    attachment = models.FileField(upload_to='letters/', null=True, blank=True)

    def __str__(self):
        return f"{self.serial_number} ({self.get_target_sector_display()})"

class SectorProfile(models.Model):
    """
    An extension to the built-in user model.
    This links a login username/password to a specific sector.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    sector = models.CharField(max_length=20, choices=SECTOR_CHOICES)

    def __str__(self):
        return f"{self.user.username} - {self.get_sector_display()}"