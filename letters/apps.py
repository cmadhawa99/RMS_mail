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
        from django.conf import settings
        import os
        import glob

        try:
            settings_obj, created = BackupSettings.objects.get_or_create(id=1)

            if settings_obj.auto_backup_enabled:
                today_str = date.today().strftime("%Y-%m-%d")
                backup_dir = settings.BACKUP_DIR

                if not os.path.exists(backup_dir):
                    os.makedirs(backup_dir)

                search_pattern = os.path.join(backup_dir, f"*AUTO_{today_str}*")
                existing_backups = glob.glob(search_pattern)

                if not existing_backups:
                    success, result = run_db_backup(is_auto=True)
                    if success:
                        settings_obj.last_auto_backup_date = date.today()
                        settings_obj.save()
        except Exception:
            pass