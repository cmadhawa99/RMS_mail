# Register your models here.

from django.contrib import admin
from .models import Letter, SectorProfile

class LetterAdmin(admin.ModelAdmin):
    list_display = ('serial_number', 'date_received', 'sender_details', 'administrated_by', 'status')
    list_filter = ('administrated_by', 'status', 'date_received')
    search_fields = ('serial_number', 'sender_details')

admin.site.register(Letter, LetterAdmin)
admin.site.register(SectorProfile)

