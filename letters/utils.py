import os
import subprocess
from datetime import datetime
from django.conf import settings
from .models import BackupSettings

def run_db_backup(is_auto=False):
    backup_dir = settings.BACKUP_DIR
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    db_name = settings.DATABASES['default']['NAME']
    db_user = settings.DATABASES['default']['USER']
    db_host = settings.DATABASES['default']['HOST']
    db_port = settings.DATABASES['default']['PORT']
    db_password = settings.DATABASES['default']['PASSWORD']

    prefix = "AUTO" if is_auto else "MANUAL"
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    filename = f"{db_name}_{prefix}_{timestamp}.backup"
    filepath = os.path.join(backup_dir, filename)

    os.environ['PGPASSWORD'] = db_password

    command = [
        'pg_dump',
        '-h', db_host,
        '-p', str(db_port),
        '-U', db_user,
        '-F', 'c',  # Custom format (compressed)
        '-f', filepath,
        db_name
    ]

    try:
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True, filepath
    except subprocess.CalledProcessError as e:
        return False, str(e.stderr)
    except FileNotFoundError:
        return False, "pg_dump not found. Ensure PostgreSQL bin folder is in your Windows system PATH."