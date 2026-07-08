import os
from io import BytesIO
from PIL import Image, ImageEnhance, ImageOps
from django.db import models
from django.contrib.auth.models import User
from django.core.files.uploadedfile import UploadedFile, InMemoryUploadedFile

# Create your models here.

from django.db import models
from django.contrib.auth.models import User

OFFICER_CHOICES = [
    ('-', '-'),
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

STATUS_CHOICES = [
    ('PENDING', 'Pending'),
    ('REPLIED', 'Replied'),
    ('NOT_REQUIRED', 'Not Required'),
    ('OLD_RECORD', 'Old Record'),
]

def letter_directory_path (instance, filename):
    return f'letters/{instance.serial_number}/{filename}'

def process_scanned_image(image_field, field_name):
    if not image_field:
        return image_field

    img = Image.open(image_field)

    img = ImageOps.exif_transpose(img)

    img = img.convert('L')

    contrast_enhancer = ImageEnhance.Contrast(img)
    img = contrast_enhancer.enhance(1.8)

    sharpness_enhancer = ImageEnhance.Sharpness(img)
    img = sharpness_enhancer.enhance(2.0)

    max_size = (1200, 1600)
    img.thumbnail(max_size, Image.Resampling.LANCZOS)

    output = BytesIO()

    img.save(output, format='JPEG', quality=60, optimize=True)
    output.seek(0)

    filename = f"{field_name}.jpg"

    new_image = InMemoryUploadedFile (
        output,
        'FileField',
        filename,
        'image/jpeg',
        output.tell(),
        None
    )

    return new_image


class Letter(models.Model):
    """The blueprint for every incoming letter"""

    serial_number = models.IntegerField(unique=True, verbose_name="අනු අංකය")
    date_received = models.DateField(blank=True, null=True)
    sender_name = models.CharField(max_length=255, blank=True, null=True)
    sender_address = models.TextField(blank=True, null=True)
    letter_type = models.CharField(max_length=255, blank=True, null=True)
    accepting_officer_id = models.CharField(max_length=50, blank=True, null=True)
    target_sector = models.CharField(max_length=20, choices=SECTOR_CHOICES, blank=True, null=True)
    administrated_by = models.CharField(max_length=20, choices=OFFICER_CHOICES, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    replied_at = models.DateTimeField(null=True, blank=True)

    attachment_1 = models.FileField(upload_to=letter_directory_path, null=True, blank=True)
    attachment_2 = models.FileField(upload_to=letter_directory_path, null=True, blank=True)
    attachment_3 = models.FileField(upload_to=letter_directory_path, null=True, blank=True)
    attachment_4 = models.FileField(upload_to=letter_directory_path, null=True, blank=True)
    attachment_5 = models.FileField(upload_to=letter_directory_path, null=True, blank=True)
    attachment_6 = models.FileField(upload_to=letter_directory_path, null=True, blank=True)

    class Meta:
        ordering = ['serial_number']

    def __str__(self):
        return f"{self.serial_number} ({self.get_target_sector_display()})"


    def save(self, *args, **kwargs):
        attachment_fields = [
            'attachment_1', 'attachment_2', 'attachment_3',
            'attachment_4', 'attachment_5', 'attachment_6'
        ]

        for field_name in attachment_fields:
            field = getattr(self, field_name)

            if field and isinstance(field.file, UploadedFile):
                try:
                    processed_file = process_scanned_image(field, field_name)
                    setattr(self, field_name, processed_file)
                except Exception as e:
                    ext = os.path.splitext(field.name)[1]
                    field.name = f"{field_name}{ext}"

        super().save(*args, **kwargs)

class SectorProfile(models.Model):
    """
    An extension to the built-in user model.
    This links a login username/password to a specific sector.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    sector = models.CharField(max_length=20, choices=SECTOR_CHOICES)

    def __str__(self):
        return f"{self.user.username} - {self.get_sector_display()}"

class LetterImage(models.Model):
    letter = models.ForeignKey(Letter, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='letters/pages/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Page for Letter #{self.letter.serial_number}"