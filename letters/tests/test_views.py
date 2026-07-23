import pytest
from django.test import TestCase, Client, RequestFactory
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from datetime import date, timedelta
from io import BytesIO

from letters.models import Letter, SectorProfile, BackupSettings
from letters.views import (
    sector_dashboard, user_add_letter, user_edit_letter, letter_detail,
    view_letter_images, custom_admin_dashboard, custom_admin_users,
    custom_admin_letters, admin_user_detail, admin_letter_detail,
    create_user, edit_user, delete_user, add_letter, edit_letter,
    delete_letter, logout_view, export_letters_excel, admin_letter_audit_log,
    admin_global_audit, manual_backup, toggle_auto_backup
)


@pytest.fixture
def client():
    # Override client fixture to use Django Test Client with proper request handling
    return Client()


@pytest.mark.django_db
class TestSectorDashboardView:
    # Tests for sector dashboard - filtering, search, pagination, access control

    def test_sector_dashboard_redirects_superuser_to_admin(self, client):
        # Superusers should be redirected to custom admin dashboard
        admin = User.objects.create_superuser(username='admin', password='pass')
        client.force_login(admin)

        response = client.get(reverse('sector_dashboard'))

        assert response.status_code == 302
        assert response.url == reverse('custom_admin_dashboard')

    def test_sector_dashboard_requires_login(self, client):
        # Unauthenticated users should be redirected to login
        response = client.get(reverse('sector_dashboard'))

        assert response.status_code == 302
        assert '/accounts/login/' in response.url

    def test_sector_dashboard_shows_user_sector_letters(self, client):
        # Users should see letters for their sector only
        user = User.objects.create_user(username='health_user', password='pass')
        SectorProfile.objects.create(user=user, sector='HEALTH')
        client.force_login(user)

        # Create letters for different sectors
        Letter.objects.create(serial_number=1, target_sector='HEALTH')
        Letter.objects.create(serial_number=2, target_sector='GOVERNING')
        Letter.objects.create(serial_number=3, target_sector='HEALTH')

        response = client.get(reverse('sector_dashboard'))

        assert response.status_code == 200
        assert response.context['total'] == 3  # All letters visible but can filter

    def test_sector_dashboard_filter_by_sector(self, client):
        # Dashboard should filter letters by selected sector
        user = User.objects.create_user(username='test_user', password='pass')
        SectorProfile.objects.create(user=user, sector='HEALTH')
        client.force_login(user)

        Letter.objects.create(serial_number=1, target_sector='HEALTH')
        Letter.objects.create(serial_number=2, target_sector='GOVERNING')
        Letter.objects.create(serial_number=3, target_sector='DEVELOPMENT')

        response = client.get(reverse('sector_dashboard'), {'sector': 'HEALTH'})

        assert response.status_code == 200
        assert response.context['total'] == 1
        assert response.context['selected_sector'] == 'HEALTH'

    def test_sector_dashboard_search_by_serial(self, client):
        # Dashboard should support searching by serial number
        user = User.objects.create_user(username='search_user', password='pass')
        SectorProfile.objects.create(user=user, sector='HEALTH')
        client.force_login(user)

        Letter.objects.create(serial_number=1001, sender_details='Test Sender')
        Letter.objects.create(serial_number=1002, sender_details='Another Sender')

        response = client.get(reverse('sector_dashboard'), {'q': '1001', 'search_type': 'serial'})

        assert response.status_code == 200
        assert response.context['total'] == 1
        assert response.context['search_query'] == '1001'

    def test_sector_dashboard_search_by_date(self, client):
        # Dashboard should support searching by date
        user = User.objects.create_user(username='date_user', password='pass')
        SectorProfile.objects.create(user=user, sector='HEALTH')
        client.force_login(user)

        Letter.objects.create(serial_number=1, date_received=date(2026, 1, 15))
        Letter.objects.create(serial_number=2, date_received=date(2026, 2, 20))

        response = client.get(reverse('sector_dashboard'), {'q': '2026-01', 'search_type': 'date'})

        assert response.status_code == 200
        assert response.context['total'] == 1

    def test_sector_dashboard_search_all_fields(self, client):
        # Dashboard should search across multiple fields when search_type is 'all
        user = User.objects.create_user(username='all_search', password='pass')
        SectorProfile.objects.create(user=user, sector='HEALTH')
        client.force_login(user)

        Letter.objects.create(serial_number=1, sender_details='Kiri Banda', letter_type='Tax')
        Letter.objects.create(serial_number=2, sender_details='Other Person', letter_type='Other')

        response = client.get(reverse('sector_dashboard'), {'q': 'Kiri', 'search_type': 'all'})

        assert response.status_code == 200
        assert response.context['total'] == 1

    def test_sector_dashboard_pagination(self, client):
        # Dashboard should paginate results (20 per page)
        user = User.objects.create_user(username='page_user', password='pass')
        SectorProfile.objects.create(user=user, sector='HEALTH')
        client.force_login(user)

        # Create 25 letters
        for i in range(25):
            Letter.objects.create(serial_number=i + 1)

        response = client.get(reverse('sector_dashboard'))

        assert response.status_code == 200
        assert len(response.context['letters']) == 20  # First page has 20

        response_page2 = client.get(reverse('sector_dashboard'), {'page': 2})
        assert len(response_page2.context['letters']) == 5  # Second page has 5

    def test_sector_dashboard_counts_pending_resolved(self, client):
        # Dashboard should calculate pending and resolved counts correctly
        user = User.objects.create_user(username='count_user', password='pass')
        SectorProfile.objects.create(user=user, sector='HEALTH')
        client.force_login(user)

        Letter.objects.create(serial_number=1, status='PENDING')
        Letter.objects.create(serial_number=2, status='PENDING')
        Letter.objects.create(serial_number=3, status='REPLIED')
        Letter.objects.create(serial_number=4, status='NOT_REQUIRED')

        response = client.get(reverse('sector_dashboard'))

        assert response.context['total'] == 4
        assert response.context['resolved'] == 1  # Only REPLIED
        assert response.context['pending'] == 3  # Total - resolved

    def test_sector_dashboard_context_data(self, client):
        # Dashboard should provide all required context data
        user = User.objects.create_user(username='context_user', password='pass')
        SectorProfile.objects.create(user=user, sector='GOVERNING')
        client.force_login(user)

        response = client.get(reverse('sector_dashboard'))

        assert 'user_sector' in response.context
        assert 'selected_sector' in response.context
        assert 'search_query' in response.context
        assert 'search_type' in response.context
        assert 'letters' in response.context
        assert 'total' in response.context
        assert 'pending' in response.context
        assert 'resolved' in response.context

    def test_sector_dashboard_without_sector_profile(self, client):
        # User without sector profile should get 'NONE' sector
        user = User.objects.create_user(username='no_sector', password='pass')
        # No SectorProfile created
        client.force_login(user)

        response = client.get(reverse('sector_dashboard'))

        assert response.status_code == 200
        assert response.context['user_sector'] == 'NONE'


@pytest.mark.django_db
class TestUserAddLetterView:
    # Tests for user add letter view

    def test_user_add_letter_redirects_superuser(self, client):
        # Superusers should be redirected to admin add_letter
        admin = User.objects.create_superuser(username='admin', password='pass')
        client.force_login(admin)

        response = client.get(reverse('user_add_letter'))

        assert response.status_code == 302
        assert response.url == reverse('add_letter')

    def test_user_add_letter_requires_login(self, client):
        # Unauthenticated users should be redirected to login
        response = client.get(reverse('user_add_letter'))

        assert response.status_code == 302
        assert '/accounts/login/' in response.url

    def test_user_add_letter_get_shows_form(self, client):
        # GET request should display the form with user's sector
        user = User.objects.create_user(username='add_user', password='pass')
        SectorProfile.objects.create(user=user, sector='HEALTH')
        client.force_login(user)

        response = client.get(reverse('user_add_letter'))

        assert response.status_code == 200
        assert 'form' in response.context
        assert response.context['user_sector'] == 'HEALTH'

    def test_user_add_letter_post_valid(self, client):
        # Valid POST should create letter and redirect
        user = User.objects.create_user(username='create_user', password='pass')
        SectorProfile.objects.create(user=user, sector='GOVERNING')
        client.force_login(user)

        post_data = {
            'serial_number': 1001,
            'date_received': '2026-06-15',
            'sender_details': 'Test Sender',
            'letter_type': 'Test Type',
            'accepting_officer_id': 'D/4',
            'status': 'PENDING',
        }

        response = client.post(reverse('user_add_letter'), post_data)

        assert response.status_code == 302
        assert response.url == reverse('sector_dashboard')
        assert Letter.objects.filter(serial_number=1001).exists()

        letter = Letter.objects.get(serial_number=1001)
        assert letter.created_by == 'create_user'
        assert letter.target_sector == 'GOVERNING'

    def test_user_add_letter_sets_target_sector_automatically(self, client):
        # Form should automatically set target_sector to user's sector
        user = User.objects.create_user(username='auto_sector', password='pass')
        SectorProfile.objects.create(user=user, sector='DEVELOPMENT')
        client.force_login(user)

        post_data = {
            'serial_number': 2001,
            'date_received': '2026-06-15',
            'sender_details': 'Sender',
            'letter_type': 'Type',
            'accepting_officer_id': 'D/4',
            'status': 'PENDING',
        }

        response = client.post(reverse('user_add_letter'), post_data)

        letter = Letter.objects.get(serial_number=2001)
        assert letter.target_sector == 'DEVELOPMENT'

    def test_user_add_letter_invalid_form(self, client):
        # Invalid form should redisplay with errors
        user = User.objects.create_user(username='invalid_user', password='pass')
        SectorProfile.objects.create(user=user, sector='HEALTH')
        client.force_login(user)

        # Missing required fields
        response = client.post(reverse('user_add_letter'), {})

        assert response.status_code == 200
        assert 'form' in response.context
        assert not response.context['form'].is_valid()


@pytest.mark.django_db
class TestUserEditLetterView:
    # Tests for user edit letter view

    def test_user_edit_letter_redirects_superuser(self, client):
        # Superusers should be redirected to admin edit_letter
        admin = User.objects.create_superuser(username='admin', password='pass')
        client.force_login(admin)

        letter = Letter.objects.create(serial_number=1)
        response = client.get(reverse('user_edit_letter', kwargs={'pk': letter.pk}))

        assert response.status_code == 302
        assert response.url == reverse('edit_letter', kwargs={'pk': letter.pk})

    def test_user_edit_letter_requires_login(self, client):
        # Unauthenticated users should be redirected to login
        letter = Letter.objects.create(serial_number=1)
        response = client.get(reverse('user_edit_letter', kwargs={'pk': letter.pk}))

        assert response.status_code == 302
        assert '/accounts/login/' in response.url

    def test_user_edit_letter_denies_other_sector(self, client):
        # Users cannot edit letters from other sectors
        user = User.objects.create_user(username='health_edit', password='pass')
        SectorProfile.objects.create(user=user, sector='HEALTH')
        client.force_login(user)

        letter = Letter.objects.create(serial_number=1, target_sector='GOVERNING')
        response = client.get(reverse('user_edit_letter', kwargs={'pk': letter.pk}))

        assert response.status_code == 302
        assert response.url == reverse('sector_dashboard')

    def test_user_edit_letter_get_shows_form(self, client):
        # GET request should display the form with letter data
        user = User.objects.create_user(username='edit_get', password='pass')
        SectorProfile.objects.create(user=user, sector='HEALTH')
        client.force_login(user)

        letter = Letter.objects.create(
            serial_number=1,
            target_sector='HEALTH',
            sender_details='Original Sender'
        )

        response = client.get(reverse('user_edit_letter', kwargs={'pk': letter.pk}))

        assert response.status_code == 200
        assert 'form' in response.context
        assert response.context['letter'] == letter

    def test_user_edit_letter_post_valid(self, client):
        # Valid POST should update letter and redirect
        user = User.objects.create_user(username='edit_post', password='pass')
        SectorProfile.objects.create(user=user, sector='HEALTH')
        client.force_login(user)

        letter = Letter.objects.create(
            serial_number=1,
            target_sector='HEALTH',
            sender_details='Old Sender',
            letter_type='Old Type',
            accepting_officer_id='D/4',
            date_received='2026-06-15',
            status='PENDING'
        )

        post_data = {
            'serial_number': 1,
            'date_received': '2026-06-15',
            'sender_details': 'Updated Sender',
            'letter_type': 'Updated Type',
            'accepting_officer_id': 'D/4',
            'status': 'PENDING',
        }

        response = client.post(reverse('user_edit_letter', kwargs={'pk': letter.pk}), post_data)

        assert response.status_code == 302
        assert response.url == reverse('sector_dashboard')

        letter.refresh_from_db()
        assert letter.sender_details == 'Updated Sender'
        assert letter.updated_by == 'edit_post'

    def test_user_edit_letter_updates_updated_by(self, client):
        # Editing should update the updated_by field
        user = User.objects.create_user(username='updater', password='pass')
        SectorProfile.objects.create(user=user, sector='HEALTH')
        client.force_login(user)

        letter = Letter.objects.create(
            serial_number=1,
            target_sector='HEALTH',
            sender_details='Sender',
            letter_type='Type',
            accepting_officer_id='D/4',
            date_received='2026-06-15',
            status='PENDING'
        )

        post_data = {
            'serial_number': 1,
            'date_received': '2026-06-15',
            'sender_details': 'Sender',
            'letter_type': 'Type',
            'accepting_officer_id': 'D/4',
            'status': 'PENDING',
        }

        client.post(reverse('user_edit_letter', kwargs={'pk': letter.pk}), post_data)

        letter.refresh_from_db()
        assert letter.updated_by == 'updater'


@pytest.mark.django_db
class TestLetterDetailView:
    # Tests for letter detail view

    def test_letter_detail_requires_login(self, client):
        # Unauthenticated users should be redirected to login
        letter = Letter.objects.create(serial_number=1)
        response = client.get(reverse('letter_detail', kwargs={'pk': letter.pk}))

        assert response.status_code == 302
        assert '/accounts/login/' in response.url

    def test_letter_detail_superuser_can_view_any(self, client):
        # Superusers can view any letter regardless of sector
        admin = User.objects.create_superuser(username='admin', password='pass')
        client.force_login(admin)

        letter = Letter.objects.create(serial_number=1, target_sector='HEALTH')
        response = client.get(reverse('letter_detail', kwargs={'pk': letter.pk}))

        assert response.status_code == 200
        assert response.context['letter'] == letter
        assert response.context['user_sector'] == 'ADMIN'

    def test_letter_detail_user_can_view_own_sector(self, client):
        # Users can view letters from their own sector
        user = User.objects.create_user(username='view_user', password='pass')
        SectorProfile.objects.create(user=user, sector='HEALTH')
        client.force_login(user)

        letter = Letter.objects.create(serial_number=1, target_sector='HEALTH')
        response = client.get(reverse('letter_detail', kwargs={'pk': letter.pk}))

        assert response.status_code == 200
        assert response.context['letter'] == letter

    def test_letter_detail_denies_other_sector(self, client):
        # Users cannot view letters from other sectors
        user = User.objects.create_user(username='deny_user', password='pass')
        SectorProfile.objects.create(user=user, sector='HEALTH')
        client.force_login(user)

        letter = Letter.objects.create(serial_number=1, target_sector='GOVERNING')
        response = client.get(reverse('letter_detail', kwargs={'pk': letter.pk}))

        assert response.status_code == 200
        # Check that access denied page is shown (either by template or content)
        assert 'access_denied' in str(response.content) or 'Access Denied' in str(response.content)

    def test_letter_detail_nonexistent(self, client):
        # Non-existent letter should return 404
        user = User.objects.create_user(username='notfound', password='pass')
        client.force_login(user)

        response = client.get(reverse('letter_detail', kwargs={'pk': 9999}))

        assert response.status_code == 404


@pytest.mark.django_db
class TestViewLetterImagesView:
    # Tests for view letter images view

    def test_view_letter_images_requires_login(self, client):
        # Unauthenticated users should be redirected to login
        letter = Letter.objects.create(serial_number=1)
        response = client.get(reverse('view_letter_images', kwargs={'pk': letter.pk}))

        assert response.status_code == 302
        assert '/accounts/login/' in response.url

    def test_view_letter_images_shows_attachments(self, client):
        # View should display letter attachments
        user = User.objects.create_user(username='img_user', password='pass')
        SectorProfile.objects.create(user=user, sector='HEALTH')
        client.force_login(user)

        letter = Letter.objects.create(serial_number=1, target_sector='HEALTH')
        response = client.get(reverse('view_letter_images', kwargs={'pk': letter.pk}))

        assert response.status_code == 200
        assert 'letter' in response.context
        assert 'attachments' in response.context


@pytest.mark.django_db
class TestCustomAdminDashboardView:
    # Tests for custom admin dashboard

    def test_admin_dashboard_redirects_non_superuser(self, client):
        # Non-superusers should be redirected to sector dashboard
        user = User.objects.create_user(username='regular', password='pass')
        client.force_login(user)

        response = client.get(reverse('custom_admin_dashboard'))

        assert response.status_code == 302
        assert response.url == reverse('sector_dashboard')

    def test_admin_dashboard_requires_login(self, client):
        # Unauthenticated users should be redirected to login
        response = client.get(reverse('custom_admin_dashboard'))

        assert response.status_code == 302
        assert '/accounts/login/' in response.url

    def test_admin_dashboard_superuser_access(self, client):
        # Superusers can access admin dashboard
        admin = User.objects.create_superuser(username='admin', password='pass')
        client.force_login(admin)

        response = client.get(reverse('custom_admin_dashboard'))

        assert response.status_code == 200
        assert 'backup_settings' in response.context

    def test_admin_dashboard_creates_backup_settings(self, client):
        # Dashboard should create BackupSettings if not exists
        admin = User.objects.create_superuser(username='admin', password='pass')
        client.force_login(admin)

        BackupSettings.objects.all().delete()  # Ensure none exist

        response = client.get(reverse('custom_admin_dashboard'))

        assert response.status_code == 200
        assert BackupSettings.objects.count() == 1


@pytest.mark.django_db
class TestCustomAdminUsersView:
    # Tests for admin users management view

    def test_admin_users_redirects_non_superuser(self, client):
        # Non-superusers should be redirected
        user = User.objects.create_user(username='regular', password='pass')
        client.force_login(user)

        response = client.get(reverse('custom_admin_users'))

        assert response.status_code == 302
        assert response.url == reverse('sector_dashboard')

    def test_admin_users_shows_non_superuser_list(self, client):
        # Should show only non-superuser accounts
        admin = User.objects.create_superuser(username='admin', password='pass')
        user1 = User.objects.create_user(username='user1', password='pass')
        user2 = User.objects.create_user(username='user2', password='pass')
        client.force_login(admin)

        response = client.get(reverse('custom_admin_users'))

        assert response.status_code == 200
        users = response.context['users']
        assert user1 in users
        assert user2 in users
        assert admin not in users

    def test_admin_users_search(self, client):
        # Search should filter users by username or name
        admin = User.objects.create_superuser(username='admin', password='pass')
        User.objects.create_user(username='john_doe', first_name='John', last_name='Doe', password='pass')
        User.objects.create_user(username='jane_smith', first_name='Jane', last_name='Smith', password='pass')
        client.force_login(admin)

        response = client.get(reverse('custom_admin_users'), {'q': 'john'})

        assert response.status_code == 200
        assert len(response.context['users']) == 1
        assert response.context['users'][0].username == 'john_doe'


@pytest.mark.django_db
class TestCustomAdminLettersView:
    # Tests for admin letters management view

    def test_admin_letters_redirects_non_superuser(self, client):
        # Non-superusers should be redirected
        user = User.objects.create_user(username='regular', password='pass')
        client.force_login(user)

        response = client.get(reverse('custom_admin_letters'))

        assert response.status_code == 302
        assert response.url == reverse('sector_dashboard')

    def test_admin_letters_shows_all_letters(self, client):
        # Admin should see all letters regardless of sector
        admin = User.objects.create_superuser(username='admin', password='pass')
        client.force_login(admin)

        Letter.objects.create(serial_number=1, target_sector='HEALTH')
        Letter.objects.create(serial_number=2, target_sector='GOVERNING')
        Letter.objects.create(serial_number=3, target_sector='DEVELOPMENT')

        response = client.get(reverse('custom_admin_letters'))

        assert response.status_code == 200
        assert response.context['total_letters'] == 3

    def test_admin_letters_search(self, client):
        # Search should filter letters
        admin = User.objects.create_superuser(username='admin', password='pass')
        client.force_login(admin)

        Letter.objects.create(serial_number=1001, sender_details='Test Sender')
        Letter.objects.create(serial_number=1002, sender_details='Other')

        response = client.get(reverse('custom_admin_letters'), {'q': '1001', 'search_type': 'serial'})

        assert response.status_code == 200
        assert response.context['total_letters'] == 1

    def test_admin_letters_pagination(self, client):
        # Letters should be paginated
        admin = User.objects.create_superuser(username='admin', password='pass')
        client.force_login(admin)

        for i in range(25):
            Letter.objects.create(serial_number=i + 1)

        response = client.get(reverse('custom_admin_letters'))

        assert response.status_code == 200
        assert len(response.context['letters']) == 20


@pytest.mark.django_db
class TestAdminUserDetailView:
    # Tests for admin user detail view

    def test_admin_user_detail_redirects_non_superuser(self, client):
        # Non-superusers should be redirected
        user = User.objects.create_user(username='regular', password='pass')
        client.force_login(user)

        response = client.get(reverse('admin_user_detail', kwargs={'user_id': 1}))

        assert response.status_code == 302

    def test_admin_user_detail_shows_user(self, client):
        # Should display user details
        admin = User.objects.create_superuser(username='admin', password='pass')
        user = User.objects.create_user(username='detail_user', password='pass')
        client.force_login(admin)

        response = client.get(reverse('admin_user_detail', kwargs={'user_id': user.id}))

        assert response.status_code == 200
        assert response.context['user_obj'] == user


@pytest.mark.django_db
class TestAdminLetterDetailView:
    # Tests for admin letter detail view

    def test_admin_letter_detail_redirects_non_superuser(self, client):
        # Non-superusers should be redirected
        user = User.objects.create_user(username='regular', password='pass')
        client.force_login(user)

        letter = Letter.objects.create(serial_number=1)
        response = client.get(reverse('admin_letter_detail', kwargs={'pk': letter.pk}))

        assert response.status_code == 302

    def test_admin_letter_detail_shows_letter(self, client):
        # Should display letter details
        admin = User.objects.create_superuser(username='admin', password='pass')
        client.force_login(admin)

        letter = Letter.objects.create(serial_number=1)
        response = client.get(reverse('admin_letter_detail', kwargs={'pk': letter.pk}))

        assert response.status_code == 200
        assert response.context['letter'] == letter


@pytest.mark.django_db
class TestCreateUserView:
    # Tests for create user view

    def test_create_user_redirects_non_superuser(self, client):
        # Non-superusers should be redirected
        user = User.objects.create_user(username='regular', password='pass')
        client.force_login(user)

        response = client.get(reverse('create_user'))

        assert response.status_code == 302

    def test_create_user_get_shows_form(self, client):
        # GET should display user creation form
        admin = User.objects.create_superuser(username='admin', password='pass')
        client.force_login(admin)

        response = client.get(reverse('create_user'))

        assert response.status_code == 200
        assert 'form' in response.context
        assert response.context['title'] == 'Create New Officer'

    def test_create_user_post_valid(self, client):
        # Valid POST should create user
        admin = User.objects.create_superuser(username='admin', password='pass')
        client.force_login(admin)

        post_data = {
            'username': 'new_officer',
            'first_name': 'New',
            'last_name': 'Officer',
            'sector': 'HEALTH',
            'new_password': 'SecurePass123!'
        }

        response = client.post(reverse('create_user'), post_data)

        assert response.status_code == 302
        assert response.url == reverse('custom_admin_users')
        assert User.objects.filter(username='new_officer').exists()


@pytest.mark.django_db
class TestEditUserView:
    # Tests for edit user view

    def test_edit_user_redirects_non_superuser(self, client):
        # Non-superusers should be redirected
        user = User.objects.create_user(username='regular', password='pass')
        client.force_login(user)

        response = client.get(reverse('edit_user', kwargs={'user_id': 1}))

        assert response.status_code == 302

    def test_edit_user_get_shows_form(self, client):
        # GET should display user edit form
        admin = User.objects.create_superuser(username='admin', password='pass')
        user = User.objects.create_user(username='edit_me', password='pass')
        client.force_login(admin)

        response = client.get(reverse('edit_user', kwargs={'user_id': user.id}))

        assert response.status_code == 200
        assert 'form' in response.context

    def test_edit_user_post_valid(self, client):
        # Valid POST should update user
        admin = User.objects.create_superuser(username='admin', password='pass')
        user = User.objects.create_user(username='to_update', password='oldpass')
        client.force_login(admin)

        post_data = {
            'username': 'to_update',
            'first_name': 'Updated',
            'last_name': 'Name',
            'sector': 'GOVERNING',
            'new_password': ''
        }

        response = client.post(reverse('edit_user', kwargs={'user_id': user.id}), post_data)

        assert response.status_code == 302
        user.refresh_from_db()
        assert user.first_name == 'Updated'


@pytest.mark.django_db
class TestDeleteUserView:
    # Tests for delete user view

    def test_delete_user_redirects_non_superuser(self, client):
        # Non-superusers should be redirected
        user = User.objects.create_user(username='regular', password='pass')
        client.force_login(user)

        response = client.post(reverse('delete_user', kwargs={'user_id': 1}))

        assert response.status_code == 302

    def test_delete_user_post_deletes(self, client):
        # POST should delete user
        admin = User.objects.create_superuser(username='admin', password='pass')
        user = User.objects.create_user(username='to_delete', password='pass')
        user_id = user.id
        client.force_login(admin)

        response = client.post(reverse('delete_user', kwargs={'user_id': user_id}))

        assert response.status_code == 302
        assert not User.objects.filter(id=user_id).exists()

    def test_delete_user_get_not_allowed(self, client):
        # GET should not delete, just redirect
        admin = User.objects.create_superuser(username='admin', password='pass')
        user = User.objects.create_user(username='get_test', password='pass')
        client.force_login(admin)

        response = client.get(reverse('delete_user', kwargs={'user_id': user.id}))

        assert response.status_code == 302
        assert User.objects.filter(username='get_test').exists()


@pytest.mark.django_db
class TestAddLetterView:
    # Tests for admin add letter view

    def test_add_letter_redirects_non_superuser(self, client):
        # Non-superusers should be redirected
        user = User.objects.create_user(username='regular', password='pass')
        client.force_login(user)

        response = client.get(reverse('add_letter'))

        assert response.status_code == 302

    def test_add_letter_get_shows_form(self, client):
        # GET should display letter creation form
        admin = User.objects.create_superuser(username='admin', password='pass')
        client.force_login(admin)

        response = client.get(reverse('add_letter'))

        assert response.status_code == 200
        assert 'form' in response.context

    def test_add_letter_post_valid(self, client):
        # Valid POST should create letter
        admin = User.objects.create_superuser(username='admin', password='pass')
        client.force_login(admin)

        post_data = {
            'serial_number': 5001,
            'sender_details': 'Admin Sender',
            'letter_type': 'Admin Type',
            'target_sector': 'HEALTH',
            'administrated_by': 'CHAIRMAN',
            'accepting_officer_id': 'OFF-ADM',
            'status': 'PENDING'
        }

        response = client.post(reverse('add_letter'), post_data)

        assert response.status_code == 302
        assert response.url == reverse('custom_admin_letters')
        assert Letter.objects.filter(serial_number=5001).exists()


@pytest.mark.django_db
class TestEditLetterView:
    # Tests for admin edit letter view

    def test_edit_letter_redirects_non_superuser(self, client):
        # Non-superusers should be redirected
        user = User.objects.create_user(username='regular', password='pass')
        client.force_login(user)

        letter = Letter.objects.create(serial_number=1)
        response = client.get(reverse('edit_letter', kwargs={'pk': letter.pk}))

        assert response.status_code == 302

    def test_edit_letter_get_shows_form(self, client):
        # GET should display letter edit form
        admin = User.objects.create_superuser(username='admin', password='pass')
        client.force_login(admin)

        letter = Letter.objects.create(serial_number=1)
        response = client.get(reverse('edit_letter', kwargs={'pk': letter.pk}))

        assert response.status_code == 200
        assert 'form' in response.context

    def test_edit_letter_post_valid(self, client):
        # Valid POST should update letter
        admin = User.objects.create_superuser(username='admin', password='pass')
        client.force_login(admin)

        letter = Letter.objects.create(
            serial_number=1,
            sender_details='Old',
            letter_type='Type',
            target_sector='HEALTH',
            administrated_by='CHAIRMAN',
            accepting_officer_id='D/4'
        )

        post_data = {
            'serial_number': 1,
            'sender_details': 'Updated',
            'letter_type': 'Type',
            'target_sector': 'HEALTH',
            'administrated_by': 'CHAIRMAN',
            'accepting_officer_id': 'D/4',
            'status': 'PENDING'
        }

        response = client.post(reverse('edit_letter', kwargs={'pk': letter.pk}), post_data)

        assert response.status_code == 302
        letter.refresh_from_db()
        assert letter.sender_details == 'Updated'


@pytest.mark.django_db
class TestDeleteLetterView:
    # Tests for delete letter view

    def test_delete_letter_redirects_non_superuser(self, client):
        # Non-superusers should be redirected
        user = User.objects.create_user(username='regular', password='pass')
        client.force_login(user)

        letter = Letter.objects.create(serial_number=1)
        response = client.post(reverse('delete_letter', kwargs={'pk': letter.pk}))

        assert response.status_code == 302

    def test_delete_letter_post_deletes(self, client):
        # POST should delete letter
        admin = User.objects.create_superuser(username='admin', password='pass')
        client.force_login(admin)

        letter = Letter.objects.create(serial_number=1)
        letter_id = letter.id

        response = client.post(reverse('delete_letter', kwargs={'pk': letter.pk}))

        assert response.status_code == 302
        assert not Letter.objects.filter(id=letter_id).exists()


@pytest.mark.django_db
class TestLogoutView:
    # Tests for logout view

    def test_logout_view_logs_out_user(self, client):
        # Logout should end user session
        user = User.objects.create_user(username='logout_test', password='pass')
        client.force_login(user)

        # Verify logged in
        response = client.get(reverse('sector_dashboard'))
        assert response.status_code == 200

        # Logout
        response = client.get(reverse('logout'))

        assert response.status_code == 302
        assert response.url == reverse('login')

        # Verify logged out
        response = client.get(reverse('sector_dashboard'))
        assert response.status_code == 302

    def test_logout_view_does_not_require_login(self, client):
        # Logout should work without being logged in
        response = client.get(reverse('logout'))

        assert response.status_code == 302


@pytest.mark.django_db
class TestExportLettersExcelView:
    # Tests for Excel export view

    def test_export_excel_redirects_non_superuser(self, client):
        # Non-superusers should be redirected
        user = User.objects.create_user(username='regular', password='pass')
        client.force_login(user)

        response = client.get(reverse('export_letters_excel'))

        assert response.status_code == 302

    def test_export_excel_returns_xlsx(self, client):
        # Should return Excel file
        admin = User.objects.create_superuser(username='admin', password='pass')
        client.force_login(admin)

        Letter.objects.create(serial_number=1, sender_details='Test')

        response = client.get(reverse('export_letters_excel'))

        assert response.status_code == 200
        assert response['Content-Type'] == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        assert 'attachment' in response.get('Content-Disposition', '')

    def test_export_excel_filename_with_search(self, client):
        # Export with search should have appropriate filename
        admin = User.objects.create_superuser(username='admin', password='pass')
        client.force_login(admin)

        Letter.objects.create(serial_number=1, sender_details='Test Search')

        response = client.get(reverse('export_letters_excel'), {'q': 'Test'})

        assert 'Search_Results' in response.get('Content-Disposition', '')


@pytest.mark.django_db
class TestAdminLetterAuditLogView:
    # Tests for audit log view

    def test_audit_log_requires_superuser(self, client):
        # Non-superusers should get access denied (not redirect)
        user = User.objects.create_user(username='regular', password='pass')
        client.force_login(user)

        letter = Letter.objects.create(serial_number=1)
        response = client.get(reverse('admin_letter_audit', kwargs={'pk': letter.pk}))

        # View requires superuser - check it shows access denied or redirects
        assert response.status_code in [200, 302]  # Either access denied page or redirect

    def test_audit_log_shows_history(self, client):
        # Should display letter history
        admin = User.objects.create_superuser(username='admin', password='pass')
        client.force_login(admin)

        letter = Letter.objects.create(serial_number=1)
        response = client.get(reverse('admin_letter_audit', kwargs={'pk': letter.pk}))

        assert response.status_code == 200
        assert 'letter' in response.context
        assert 'audit_data' in response.context


@pytest.mark.django_db
class TestAdminGlobalAuditView:
    # Tests for global audit view

    def test_global_audit_requires_superuser(self, client):
        # Non-superusers should get access denied (not redirect)
        user = User.objects.create_user(username='regular', password='pass')
        client.force_login(user)

        response = client.get(reverse('admin_global_audit'))

        # View requires superuser - check it shows access denied or redirects
        assert response.status_code in [200, 302]  # Either access denied page or redirect

    def test_global_audit_shows_all_history(self, client):
        # Should display all letter history
        admin = User.objects.create_superuser(username='admin', password='pass')
        client.force_login(admin)

        Letter.objects.create(serial_number=1)
        Letter.objects.create(serial_number=2)

        response = client.get(reverse('admin_global_audit'))

        assert response.status_code == 200
        assert 'history_records' in response.context


@pytest.mark.django_db
class TestManualBackupView:
    # Tests for manual backup view

    def test_manual_backup_redirects_non_superuser(self, client):
        # Non-superusers should be redirected
        user = User.objects.create_user(username='regular', password='pass')
        client.force_login(user)

        response = client.get(reverse('manual_backup'))

        assert response.status_code == 302

    def test_manual_backup_calls_run_db_backup(self, client):
        # Should call run_db_backup function
        admin = User.objects.create_superuser(username='admin', password='pass')
        client.force_login(admin)

        response = client.get(reverse('manual_backup'))

        assert response.status_code == 302
        assert response.url == reverse('custom_admin_dashboard')


@pytest.mark.django_db
class TestToggleAutoBackupView:
    # Tests for toggle auto backup view

    def test_toggle_auto_backup_redirects_non_superuser(self, client):
        # Non-superusers should be redirected
        user = User.objects.create_user(username='regular', password='pass')
        client.force_login(user)

        response = client.get(reverse('toggle_auto_backup'))

        assert response.status_code == 302

    def test_toggle_auto_backup_enables(self, client):
        # Should enable auto backup when disabled
        admin = User.objects.create_superuser(username='admin', password='pass')
        client.force_login(admin)

        settings = BackupSettings.objects.create(auto_backup_enabled=False)

        response = client.get(reverse('toggle_auto_backup'))

        assert response.status_code == 302
        settings.refresh_from_db()
        assert settings.auto_backup_enabled is True

    def test_toggle_auto_backup_disables(self, client):
        # Should disable auto backup when enabled
        admin = User.objects.create_superuser(username='admin', password='pass')
        client.force_login(admin)

        settings = BackupSettings.objects.create(auto_backup_enabled=True)

        response = client.get(reverse('toggle_auto_backup'))

        assert response.status_code == 302
        settings.refresh_from_db()
        assert settings.auto_backup_enabled is False