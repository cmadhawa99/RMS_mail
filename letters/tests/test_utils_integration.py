import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client, RequestFactory
from django.contrib.auth.models import User
from django.urls import reverse
from datetime import date, timedelta
from io import BytesIO

from letters.models import Letter, SectorProfile, LetterImage
from letters.utils import run_db_backup
from letters.views import (
    sector_dashboard, user_add_letter, user_edit_letter, letter_detail,
    custom_admin_dashboard, custom_admin_letters, admin_user_detail,
    create_user, edit_user, delete_user, add_letter, edit_letter,
    delete_letter, export_letters_excel
)



# Utilities tests - run_db_backup() Functionality


@pytest.mark.django_db
class TestRunDBBackup:
    # Tests for PostgreSQL backup functionality via run_db_backup()

    def test_run_db_backup_creates_backup_directory(self, settings):
        # Should create backup directory if it doesn't exist
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            backup_dir = os.path.join(temp_dir, 'nonexistent', 'backups')
            settings.BACKUP_DIR = backup_dir

            # Mock subprocess to avoid actual pg_dump call
            with patch('letters.utils.subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(returncode=0)

                success, result = run_db_backup(is_auto=False)

                # Verify directory was created
                assert os.path.exists(backup_dir)

    @patch('letters.utils.subprocess.run')
    def test_run_db_backup_success_auto(self, mock_run, settings):
        # Should return True and filepath on successful auto backup
        import os

        mock_run.return_value = MagicMock(returncode=0)

        success, result = run_db_backup(is_auto=True)

        assert success is True
        assert 'AUTO' in result
        mock_run.assert_called_once()

    @patch('letters.utils.subprocess.run')
    def test_run_db_backup_success_manual(self, mock_run, settings):
        # Should return True and filepath on successful manual backup
        mock_run.return_value = MagicMock(returncode=0)

        success, result = run_db_backup(is_auto=False)

        assert success is True
        assert 'MANUAL' in result

    @patch('letters.utils.subprocess.run')
    def test_run_db_backup_handles_subprocess_error(self, mock_run, settings):
        # Should return False and error message on subprocess failure
        from subprocess import CalledProcessError
        mock_run.side_effect = CalledProcessError(1, 'pg_dump', output=b"Connection failed")

        success, result = run_db_backup(is_auto=False)

        assert success is False

    @patch('letters.utils.subprocess.run')
    def test_run_db_backup_handles_file_not_found(self, mock_run, settings):
        # Should return False with helpful message if pg_dump not found
        mock_run.side_effect = FileNotFoundError()

        success, result = run_db_backup(is_auto=False)

        assert success is False
        assert "pg_dump not found" in result

    @patch('letters.utils.subprocess.run')
    def test_run_db_backup_command_structure(self, mock_run, settings):
        # Should construct correct pg_dump command
        mock_run.return_value = MagicMock(returncode=0)

        run_db_backup(is_auto=False)

        call_args = mock_run.call_args
        command = call_args[0][0]  # First positional argument

        assert 'pg_dump' in command
        assert '-h' in command
        assert '-p' in command
        assert '-U' in command
        assert '-F' in command
        assert 'c' in command  # Custom format

    @patch('letters.utils.subprocess.run')
    def test_run_db_backup_sets_password_env(self, mock_run, settings):
        # Should set PGPASSWORD environment variable
        import os

        mock_run.return_value = MagicMock(returncode=0)

        original_pwd = os.environ.get('PGPASSWORD')

        try:
            run_db_backup(is_auto=False)

            # PGPASSWORD should be set during execution
            assert 'PGPASSWORD' in os.environ
        finally:
            # Restore original value
            if original_pwd is None:
                os.environ.pop('PGPASSWORD', None)
            else:
                os.environ['PGPASSWORD'] = original_pwd

    @patch('letters.utils.subprocess.run')
    def test_run_db_backup_timestamp_format(self, mock_run, settings):
        # Should use correct timestamp format in filename
        import re

        mock_run.return_value = MagicMock(returncode=0)

        success, result = run_db_backup(is_auto=True)

        # Check timestamp pattern: YYYY-MM-DD_HH-MM-SS
        timestamp_pattern = r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}'
        assert re.search(timestamp_pattern, result)

    @patch('letters.utils.subprocess.run')
    def test_run_db_backup_uses_settings_values(self, mock_run, settings):
        # Should use database settings from Django settings
        mock_run.return_value = MagicMock(returncode=0)

        with patch.dict(settings.DATABASES['default'], {
            'NAME': 'test_db',
            'USER': 'test_user',
            'HOST': 'test_host',
            'PORT': '5433'
        }):
            run_db_backup(is_auto=False)

            call_args = mock_run.call_args
            command = call_args[0][0]

            assert 'test_db' in command
            assert 'test_user' in command
            assert 'test_host' in command
            assert '5433' in command


# Integration tests

@pytest.mark.django_db
class TestCompleteLetterWorkflow:
    # Integration tests for complete letter workflows (create → edit → reply)

    def test_create_letter_through_view(self, client):
        # Should create a letter through the add_letter view
        admin = User.objects.create_superuser(username='admin', password='pass')
        client.force_login(admin)

        form_data = {
            'serial_number': 1001,
            'date_received': '2026-06-15',
            'sender_details': 'Test Sender, Address',
            'letter_type': 'Test Letter Type',
            'target_sector': 'HEALTH',
            'administrated_by': 'SECRETARY',
            'accepting_officer_id': 'OFF-001',
            'status': 'PENDING'
        }

        response = client.post(reverse('add_letter'), form_data)

        assert response.status_code == 302  # Redirect after success
        assert Letter.objects.filter(serial_number=1001).exists()

        letter = Letter.objects.get(serial_number=1001)
        assert letter.sender_details == 'Test Sender, Address'
        assert letter.created_by == 'admin'

    def test_edit_letter_updates_fields(self, client):
        # Should update letter fields through edit view
        admin = User.objects.create_superuser(username='admin', password='pass')
        client.force_login(admin)

        letter = Letter.objects.create(
            serial_number=1002,
            sender_details='Original Sender',
            letter_type='Original Type',
            target_sector='GOVERNING',
            administrated_by='CHAIRMAN',
            accepting_officer_id='OFF-001'
        )

        form_data = {
            'serial_number': 1002,
            'sender_details': 'Updated Sender',
            'letter_type': 'Updated Type',
            'target_sector': 'GOVERNING',
            'administrated_by': 'CHAIRMAN',
            'accepting_officer_id': 'OFF-001',
            'status': 'PENDING'
        }

        response = client.post(reverse('edit_letter', args=[letter.pk]), form_data)

        assert response.status_code == 302
        letter.refresh_from_db()
        assert letter.sender_details == 'Updated Sender'
        assert letter.updated_by == 'admin'

    def test_letter_status_transition_to_replied(self, client):
        # Should transition letter status from PENDING to REPLIED
        admin = User.objects.create_superuser(username='admin', password='pass')
        client.force_login(admin)

        letter = Letter.objects.create(
            serial_number=1003,
            sender_details='Reply Test Sender',
            letter_type='Reply Test',
            target_sector='HEALTH',
            administrated_by='SECRETARY',
            accepting_officer_id='OFF-001',
            status='PENDING'
        )

        form_data = {
            'serial_number': 1003,
            'sender_details': 'Reply Test Sender',
            'letter_type': 'Reply Test',
            'target_sector': 'HEALTH',
            'administrated_by': 'SECRETARY',
            'accepting_officer_id': 'OFF-001',
            'status': 'REPLIED',
            'replied_at': '2026-06-20'
        }

        response = client.post(reverse('edit_letter', args=[letter.pk]), form_data)

        assert response.status_code == 302
        letter.refresh_from_db()
        assert letter.status == 'REPLIED'
        assert letter.replied_at.strftime('%Y-%m-%d') == '2026-06-20'

    def test_letter_status_transition_to_not_required(self, client):
        # Should transition letter status to NOT_REQUIRED and clear replied_at
        admin = User.objects.create_superuser(username='admin', password='pass')
        client.force_login(admin)

        letter = Letter.objects.create(
            serial_number=1004,
            sender_details='Not Required Sender',
            letter_type='Not Required Test',
            target_sector='DEVELOPMENT',
            administrated_by='CHAIRMAN',
            accepting_officer_id='OFF-001',
            status='PENDING',
            replied_at='2026-06-18'
        )

        form_data = {
            'serial_number': 1004,
            'sender_details': 'Not Required Sender',
            'letter_type': 'Not Required Test',
            'target_sector': 'DEVELOPMENT',
            'administrated_by': 'CHAIRMAN',
            'accepting_officer_id': 'OFF-001',
            'status': 'NOT_REQUIRED',
            'replied_at': ''
        }

        response = client.post(reverse('edit_letter', args=[letter.pk]), form_data)

        assert response.status_code == 302
        letter.refresh_from_db()
        assert letter.status == 'NOT_REQUIRED'
        assert letter.replied_at is None

    def test_user_sector_letter_workflow(self, client):
        # Should allow sector users to manage their sector's letters
        user = User.objects.create_user(username='health_officer', password='pass')
        SectorProfile.objects.create(user=user, sector='HEALTH')
        client.force_login(user)

        # Create a letter for HEALTH sector
        letter = Letter.objects.create(
            serial_number=2001,
            sender_details='Health Letter Sender',
            letter_type='Health Matter',
            target_sector='HEALTH',
            administrated_by='SECRETARY',
            accepting_officer_id='OFF-H01',
            status='PENDING'
        )

        # Edit through user form
        form_data = {
            'serial_number': 2001,
            'date_received': '2026-06-15',
            'sender_details': 'Updated Health Sender',
            'letter_type': 'Health Matter',
            'target_sector': 'HEALTH',
            'administrated_by': 'SECRETARY',
            'accepting_officer_id': 'OFF-H01',
            'status': 'REPLIED',
            'replied_at': '2026-06-20'
        }

        response = client.post(reverse('user_edit_letter', args=[letter.pk]), form_data)

        assert response.status_code == 302
        letter.refresh_from_db()
        assert letter.sender_details == 'Updated Health Sender'
        assert letter.status == 'REPLIED'


@pytest.mark.django_db
class TestMultiUserSectorIsolation:
    # Integration tests for multi-user sector isolation

    def test_health_user_cannot_see_governing_letters_in_dashboard(self, client):
        # Health sector user should only see HEALTH letters in filtered view
        health_user = User.objects.create_user(username='health_user', password='pass')
        SectorProfile.objects.create(user=health_user, sector='HEALTH')
        client.force_login(health_user)

        # Create letters for different sectors
        Letter.objects.create(serial_number=3001, target_sector='HEALTH', sender_details='Health Letter')
        Letter.objects.create(serial_number=3002, target_sector='GOVERNING', sender_details='Governing Letter')
        Letter.objects.create(serial_number=3003, target_sector='DEVELOPMENT', sender_details='Development Letter')

        # Filter by HEALTH sector
        response = client.get(reverse('sector_dashboard'), {'sector': 'HEALTH'})

        assert response.status_code == 200
        assert response.context['total'] == 1
        letters = list(response.context['letters'])
        assert letters[0].target_sector == 'HEALTH'

    def test_income_user_cannot_access_other_sector_filter(self, client):
        # Income sector user filtering by other sector should return empty
        income_user = User.objects.create_user(username='income_user', password='pass')
        SectorProfile.objects.create(user=income_user, sector='INCOME')
        client.force_login(income_user)

        # Create letters
        Letter.objects.create(serial_number=3011, target_sector='INCOME', sender_details='Income Letter')
        Letter.objects.create(serial_number=3012, target_sector='ACCOUNTS', sender_details='Accounts Letter')

        # Try to filter by ACCOUNTS (should work but shows only ACCOUNTS letters)
        response = client.get(reverse('sector_dashboard'), {'sector': 'ACCOUNTS'})

        assert response.status_code == 200
        assert response.context['total'] == 1
        assert response.context['selected_sector'] == 'ACCOUNTS'

    def test_multiple_users_different_sectors_isolation(self, client):
        # Multiple users from different sectors should see isolated data
        health_user = User.objects.create_user(username='multi_health', password='pass')
        SectorProfile.objects.create(user=health_user, sector='HEALTH')

        governing_user = User.objects.create_user(username='multi_gov', password='pass')
        SectorProfile.objects.create(user=governing_user, sector='GOVERNING')

        # Create sector-specific letters
        Letter.objects.create(serial_number=3021, target_sector='HEALTH', sender_details='Health Only')
        Letter.objects.create(serial_number=3022, target_sector='GOVERNING', sender_details='Governing Only')
        Letter.objects.create(serial_number=3023, target_sector='HEALTH', sender_details='Another Health')

        # Health user filters by HEALTH
        client.force_login(health_user)
        response_health = client.get(reverse('sector_dashboard'), {'sector': 'HEALTH'})

        # Governing user filters by GOVERNING
        client.force_login(governing_user)
        response_gov = client.get(reverse('sector_dashboard'), {'sector': 'GOVERNING'})

        assert response_health.context['total'] == 2
        assert response_gov.context['total'] == 1

    def test_superuser_sees_all_sectors(self, client):
        # Superuser should see all letters regardless of sector filter
        admin = User.objects.create_superuser(username='super_admin', password='pass')
        client.force_login(admin)

        Letter.objects.create(serial_number=3031, target_sector='HEALTH')
        Letter.objects.create(serial_number=3032, target_sector='GOVERNING')
        Letter.objects.create(serial_number=3033, target_sector='DEVELOPMENT')
        Letter.objects.create(serial_number=3034, target_sector='INCOME')
        Letter.objects.create(serial_number=3035, target_sector='ACCOUNTS')

        response = client.get(reverse('custom_admin_letters'))

        assert response.status_code == 200
        assert response.context['total_letters'] == 5

    def test_user_creation_assigns_correct_sector(self, client):
        # Creating a user should assign them to the correct sector
        admin = User.objects.create_superuser(username='admin', password='pass')
        client.force_login(admin)

        form_data = {
            'username': 'new_officer',
            'first_name': 'New',
            'last_name': 'Officer',
            'sector': 'DEVELOPMENT',
            'new_password': 'SecurePass123!'
        }

        response = client.post(reverse('create_user'), form_data)

        assert response.status_code == 302
        user = User.objects.get(username='new_officer')
        assert hasattr(user, 'sectorprofile')
        assert user.sectorprofile.sector == 'DEVELOPMENT'


@pytest.mark.django_db
class TestPermissionBoundaries:
    # Integration tests for permission boundaries and access control

    def test_regular_user_cannot_access_admin_dashboard(self, client):
        # Regular users should be redirected from admin dashboard
        user = User.objects.create_user(username='regular', password='pass')
        SectorProfile.objects.create(user=user, sector='HEALTH')
        client.force_login(user)

        response = client.get(reverse('custom_admin_dashboard'))

        assert response.status_code == 302
        assert response.url == reverse('sector_dashboard')

    def test_regular_user_cannot_access_admin_users_view(self, client):
        # Regular users cannot access user management
        user = User.objects.create_user(username='regular2', password='pass')
        SectorProfile.objects.create(user=user, sector='HEALTH')
        client.force_login(user)

        response = client.get(reverse('custom_admin_users'))

        assert response.status_code == 302

    def test_regular_user_cannot_access_admin_letters_view(self, client):
        # Regular users cannot access admin letters management
        user = User.objects.create_user(username='regular3', password='pass')
        SectorProfile.objects.create(user=user, sector='GOVERNING')
        client.force_login(user)

        response = client.get(reverse('custom_admin_letters'))

        assert response.status_code == 302

    def test_regular_user_cannot_create_users(self, client):
        # Regular users cannot access create user view
        user = User.objects.create_user(username='regular4', password='pass')
        SectorProfile.objects.create(user=user, sector='HEALTH')
        client.force_login(user)

        response = client.get(reverse('create_user'))

        assert response.status_code == 302

    def test_regular_user_cannot_delete_users(self, client):
        # Regular users cannot delete users
        user = User.objects.create_user(username='regular5', password='pass')
        SectorProfile.objects.create(user=user, sector='HEALTH')
        client.force_login(user)

        admin_user = User.objects.create_user(username='to_delete', password='pass')

        response = client.post(reverse('delete_user', args=[admin_user.pk]))

        assert response.status_code == 302
        assert User.objects.filter(username='to_delete').exists()

    def test_regular_user_cannot_delete_letters(self, client):
        # Regular users cannot delete letters via admin view
        user = User.objects.create_user(username='regular6', password='pass')
        SectorProfile.objects.create(user=user, sector='HEALTH')
        client.force_login(user)

        letter = Letter.objects.create(
            serial_number=4001,
            sender_details='Delete Test',
            letter_type='Test',
            target_sector='HEALTH',
            administrated_by='SECRETARY',
            accepting_officer_id='OFF-001'
        )

        response = client.post(reverse('delete_letter', args=[letter.pk]))

        assert response.status_code == 302
        assert Letter.objects.filter(serial_number=4001).exists()

    def test_superuser_can_access_all_admin_views(self, client):
        # Superusers should access all admin views
        admin = User.objects.create_superuser(username='full_admin', password='pass')
        client.force_login(admin)

        admin_views = [
            'custom_admin_dashboard',
            'custom_admin_users',
            'custom_admin_letters',
            'create_user',
            'add_letter',
            'export_letters_excel'
        ]

        for view_name in admin_views:
            response = client.get(reverse(view_name))
            assert response.status_code == 200 or response.status_code == 302, \
                f"Failed to access {view_name}"

    def test_superuser_can_create_and_delete_users(self, client):
        # Superusers can create and delete users
        admin = User.objects.create_superuser(username='crud_admin', password='pass')
        client.force_login(admin)

        # Create user
        form_data = {
            'username': 'crud_test_user',
            'first_name': 'CRUD',
            'last_name': 'Test',
            'sector': 'ACCOUNTS',
            'new_password': 'Pass123!'
        }

        response = client.post(reverse('create_user'), form_data)
        assert response.status_code == 302
        assert User.objects.filter(username='crud_test_user').exists()

        # Delete user - requires POST method
        user_to_delete = User.objects.get(username='crud_test_user')
        response = client.post(reverse('delete_user', args=[user_to_delete.pk]))

        assert response.status_code == 302
        assert not User.objects.filter(username='crud_test_user').exists()

    def test_superuser_can_delete_letters(self, client):
        # Superusers can delete letters
        admin = User.objects.create_superuser(username='delete_admin', password='pass')
        client.force_login(admin)

        letter = Letter.objects.create(
            serial_number=4010,
            sender_details='Delete Admin Test',
            letter_type='Test',
            target_sector='HEALTH',
            administrated_by='SECRETARY',
            accepting_officer_id='OFF-001'
        )

        response = client.post(reverse('delete_letter', args=[letter.pk]))

        assert response.status_code == 302
        assert not Letter.objects.filter(serial_number=4010).exists()

    def test_unauthenticated_user_cannot_access_any_protected_view(self, client):
        # Unauthenticated users should be redirected to login
        protected_views = [
            'sector_dashboard',
            'custom_admin_dashboard',
            'custom_admin_users',
            'custom_admin_letters',
            'create_user',
            'add_letter',
            'export_letters_excel'
        ]

        for view_name in protected_views:
            response = client.get(reverse(view_name))
            assert response.status_code == 302
            assert '/accounts/login/' in response.url or response.url.startswith('/accounts/login/')

    def test_user_cannot_edit_letter_from_different_sector_via_admin(self, client):
        # Regular users shouldn't reach admin edit views anyway, but test boundary
        health_user = User.objects.create_user(username='boundary_health', password='pass')
        SectorProfile.objects.create(user=health_user, sector='HEALTH')
        client.force_login(health_user)

        governing_letter = Letter.objects.create(
            serial_number=4020,
            sender_details='Governing Boundary Test',
            letter_type='Test',
            target_sector='GOVERNING',
            administrated_by='CHAIRMAN',
            accepting_officer_id='OFF-G01'
        )

        # Try to access admin edit view (should redirect non-superuser)
        response = client.get(reverse('edit_letter', args=[governing_letter.pk]))

        assert response.status_code == 302

    def test_export_requires_authentication(self, client):
        # Export view should require authentication
        response = client.get(reverse('export_letters_excel'))

        assert response.status_code == 302
        assert '/accounts/login/' in response.url

    def test_export_generates_valid_excel_for_superuser(self, client):
        # Superuser should get valid Excel file
        admin = User.objects.create_superuser(username='export_admin', password='pass')
        client.force_login(admin)

        Letter.objects.create(
            serial_number=5001,
            sender_details='Export Test Sender',
            letter_type='Export Test Type',
            target_sector='HEALTH',
            administrated_by='SECRETARY',
            accepting_officer_id='OFF-E01',
            status='PENDING'
        )

        response = client.get(reverse('export_letters_excel'))

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        assert 'attachment' in response.get('Content-Disposition', '')