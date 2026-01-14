# Register your models here.

from django.contrib import admin
from .models import Letter, SectorProfile

class LetterAdmin(admin.ModelAdmin):
    list_display = ('serial_number', 'date_received', 'sender_name', 'administrated_by', 'is_replied')
    list_filter = ('administrated_by', 'is_replied', 'date_received')
    search_fields = ('serial_number', 'sender_name')

admin.site.register(Letter, LetterAdmin)
admin.site.register(SectorProfile)

