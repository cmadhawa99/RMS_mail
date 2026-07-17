from django.apps import AppConfig
import sys
import threading
import time
from datetime import date


class LettersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'letters'

    def ready(self):
        if 'runserver' not in sys.argv and 'waitress' not in sys.modules:
            return

        threading.Thread(target=self.run_startup_backup, daemon=True).start()

    def run_startup_backup(self):

        time.sleep(3)

        from .models import BackupSettings
        from .utils import run_db_backup

        try:
            settings_obj, created = BackupSettings.objects.get_or_create(id=1)

            if settings_obj.auto_backup_enabled and settings_obj.last_auto_backup_date != date.today():
                success, result = run_db_backup(is_auto=True)
                if success:
                    settings_obj.last_auto_backup_date = date.today()
                    settings_obj.save()
        except Exception:
            pass