import os
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from .models import Letter

# 1. DELETE files when the Letter is deleted from Database
@receiver(post_delete, sender=Letter)
def auto_delete_file_on_delete(sender, instance, **kwargs):

    attachments = [
        instance.attachment_1, instance.attachment_2,
        instance.attachment_3, instance.attachment_4,
        instance.attachment_5, instance.attachment_6
    ]
    for file in attachments:
        if file:
            if os.path.isfile(file.path):
                os.remove(file.path)

# 2. DELETE old file when you upload a NEW one (or Clear it)
@receiver(pre_save, sender=Letter)
def auto_delete_file_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return False
    try:
        old_obj = Letter.objects.get(pk=instance.pk)
    except Letter.DoesNotExist:
        return False

    fields = ['attachment_1', 'attachment_2', 'attachment_3',
              'attachment_4', 'attachment_5', 'attachment_6']

    for field_name in fields:
        old_file = getattr(old_obj, field_name)
        new_file = getattr(instance, field_name)

        if old_file and old_file != new_file:
            if os.path.isfile(old_file.path):
                os.remove(old_file.path)