import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from letters.forms import UserForm, LetterForm, UserLetterForm
from letters.models import Letter, SectorProfile, SECTOR_CHOICES, OFFICER_CHOICES
from PIL import Image
import io


@pytest.mark.django_db
class TestUserForm:
    # Tests for UserForm - User creation and sector assignment

    def test_create_new_user_with_password(self):
        # Valid: Create new user with all required fields including password
        form_data = {
            'username': 'john_doe',
            'first_name': 'John',
            'last_name': 'Doe',
            'sector': 'GOVERNING',  # Use actual choice value
            'new_password': 'SecurePass123!'
        }
        form = UserForm(data=form_data)

        assert form.is_valid(), f"Form should be valid, errors: {form.errors}"

        user = form.save()
        assert user.username == 'john_doe'
        assert user.first_name == 'John'
        assert user.last_name == 'Doe'
        assert user.check_password('SecurePass123!')
        assert not user.is_staff
        assert not user.is_superuser

        # Verify sector profile created
        assert hasattr(user, 'sectorprofile')
        assert user.sectorprofile.sector == 'GOVERNING'

    def test_create_user_without_password_fails(self):
        # Invalid: New user without password should fail
        form_data = {
            'username': 'jane_smith',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'sector': 'HEALTH',
            'new_password': ''  # Empty password
        }
        form = UserForm(data=form_data)

        assert not form.is_valid()
        assert 'new_password' in form.errors
        assert "Password is required for new accounts." in form.errors['new_password']

    def test_update_existing_user_without_password(self):
        # Valid: Update existing user without providing password (keep current)
        user = User.objects.create_user(
            username='existing_user',
            password='OldPass123!'
        )
        SectorProfile.objects.create(user=user, sector='ACCOUNTS')

        form_data = {
            'username': 'existing_user',
            'first_name': 'Updated',
            'last_name': 'Name',
            'sector': 'ACCOUNTS',
            'new_password': ''  # Keep existing password
        }
        form = UserForm(data=form_data, instance=user)

        assert form.is_valid(), f"Form should be valid, errors: {form.errors}"
        updated_user = form.save()

        assert updated_user.first_name == 'Updated'
        assert updated_user.check_password('OldPass123!')  # Password unchanged

    def test_update_user_sector(self):
        # Valid: Update user's sector assignment
        user = User.objects.create_user(username='sector_test', password='Pass123!')
        SectorProfile.objects.create(user=user, sector='DEVELOPMENT')

        form_data = {
            'username': 'sector_test',
            'first_name': 'Sector',
            'last_name': 'Test',
            'sector': 'INCOME',
            'new_password': ''
        }
        form = UserForm(data=form_data, instance=user)

        assert form.is_valid()
        form.save()

        # Refresh from DB
        user.refresh_from_db()
        assert user.sectorprofile.sector == 'INCOME'

    def test_all_sector_choices_available(self):
        # Valid: All sector choices are available in form
        form = UserForm()
        sector_field = form.fields['sector']

        # Check all sectors from SECTOR_CHOICES are present
        form_sectors = [choice[0] for choice in sector_field.choices]
        expected_sectors = [choice[0] for choice in SECTOR_CHOICES]

        for sector in expected_sectors:
            assert sector in form_sectors

    def test_user_form_initializes_existing_sector(self):
        # Valid: Form initializes with existing user's sector
        user = User.objects.create_user(username='init_test', password='Pass123!')
        SectorProfile.objects.create(user=user, sector='HEALTH')

        form = UserForm(instance=user)
        assert form.fields['sector'].initial == 'HEALTH'


@pytest.mark.django_db
class TestLetterForm:
    # Tests for LetterForm - Letter creation and validation

    def test_create_letter_minimal_fields(self):
        # Valid: Create letter with only required fields
        form_data = {
            'serial_number': 1,
            'sender_details': 'John Doe, ABC Corp, Colombo',
            'letter_type': 'Inquiry about services',
            'target_sector': 'GOVERNING',
            'administrated_by': 'CHAIRMAN',
            'accepting_officer_id': 'OFF-123',
            'status': 'PENDING'
        }
        form = LetterForm(data=form_data)

        assert form.is_valid(), f"Form should be valid, errors: {form.errors}"
        letter = form.save()
        assert letter.serial_number == 1
        assert letter.status == 'PENDING'

    def test_serial_number_uniqueness_on_create(self):
        # Invalid: Duplicate serial number should fail on creation
        Letter.objects.create(
            serial_number=100,
            sender_details='Original Sender',
            letter_type='Original Type',
            target_sector='GOVERNING',
            administrated_by='CHAIRMAN',
            accepting_officer_id='OFF-001'
        )

        form_data = {
            'serial_number': 100,
            'sender_details': 'New Sender',
            'letter_type': 'New Type',
            'target_sector': 'HEALTH',
            'administrated_by': 'SECRETARY',
            'accepting_officer_id': 'OFF-002',
            'status': 'PENDING'
        }
        form = LetterForm(data=form_data)

        assert not form.is_valid()
        assert 'serial_number' in form.errors
        assert "already in use" in form.errors['serial_number'][0]

    def test_serial_number_uniqueness_on_update(self):
        # Invalid: Cannot change serial number to existing one on update
        letter1 = Letter.objects.create(
            serial_number=201,
            sender_details='Sender 1',
            letter_type='Type 1',
            target_sector='GOVERNING',
            administrated_by='CHAIRMAN',
            accepting_officer_id='OFF-001'
        )
        letter2 = Letter.objects.create(
            serial_number=202,
            sender_details='Sender 2',
            letter_type='Type 2',
            target_sector='HEALTH',
            administrated_by='SECRETARY',
            accepting_officer_id='OFF-002'
        )

        # Try to change letter2's serial to letter1's serial
        form_data = {
            'serial_number': 201,
            'sender_details': 'Sender 2 Updated',
            'letter_type': 'Type 2 Updated',
            'target_sector': 'HEALTH',
            'administrated_by': 'SECRETARY',
            'accepting_officer_id': 'OFF-002',
            'status': 'PENDING'
        }
        form = LetterForm(data=form_data, instance=letter2)

        assert not form.is_valid()
        assert 'serial_number' in form.errors
        assert "already exists" in form.errors['serial_number'][0]

    def test_same_serial_number_on_update_allowed(self):
        # Valid: Keeping same serial number on update is allowed
        letter = Letter.objects.create(
            serial_number=301,
            sender_details='Original Sender',
            letter_type='Original Type',
            target_sector='GOVERNING',
            administrated_by='CHAIRMAN',
            accepting_officer_id='OFF-001'
        )

        form_data = {
            'serial_number': 301,  # Same as before
            'sender_details': 'Updated Sender Details',
            'letter_type': 'Updated Type',
            'target_sector': 'GOVERNING',
            'administrated_by': 'CHAIRMAN',
            'accepting_officer_id': 'OFF-001',
            'status': 'PENDING'
        }
        form = LetterForm(data=form_data, instance=letter)

        assert form.is_valid(), f"Form should be valid, errors: {form.errors}"
        updated_letter = form.save()
        assert updated_letter.sender_details == 'Updated Sender Details'

    def test_letter_with_attachments(self):
        # Valid: Create letter with image attachments (simulating scanned docs).
        # Create a real in-memory JPEG image (100x100 pixels, red)
        img_file = io.BytesIO()
        image = Image.new('RGB', (100, 100), color='red')
        image.save(img_file, format='JPEG')
        img_file.seek(0)  # Reset pointer to start

        # Wrap in Django's SimpleUploadedFile
        test_image = SimpleUploadedFile(
            "scan_page_1.jpg",
            img_file.read(),
            content_type="image/jpeg"
        )

        form_data = {
            'serial_number': 401,
            'sender_details': 'Sender with image attachment',
            'letter_type': 'Scanned Letter',
            'target_sector': 'GOVERNING',
            'administrated_by': 'CHAIRMAN',
            'accepting_officer_id': 'OFF-001',
            'status': 'PENDING'
        }
        # Note: Ensure your form uses 'attachment_1' or update to match your actual field name
        form = LetterForm(data=form_data, files={'attachment_1': test_image})

        assert form.is_valid(), f"Form should be valid, errors: {form.errors}"
        letter = form.save()

        # Verify the image was saved and processed
        assert letter.attachment_1, "Attachment should exist"
        assert letter.attachment_1.name.endswith('.jpg'), "File should retain image extension"

    def test_letter_with_dates(self):
        # Valid: Create letter with received and reply dates
        form_data = {
            'serial_number': 501,
            'date_received': '2026-06-15',
            'replied_at': '2026-06-20',
            'sender_details': 'Date Test Sender',
            'letter_type': 'Date Test Type',
            'target_sector': 'GOVERNING',
            'administrated_by': 'CHAIRMAN',
            'accepting_officer_id': 'OFF-001',
            'status': 'REPLIED'
        }
        form = LetterForm(data=form_data)

        assert form.is_valid(), f"Form should be valid, errors: {form.errors}"
        letter = form.save()
        assert str(letter.date_received) == '2026-06-15'
        assert letter.replied_at.strftime('%Y-%m-%d') == '2026-06-20'

    def test_all_status_choices_available(self):
        # Valid: All status choices are available in form
        form = LetterForm()
        status_field = form.fields['status']

        # Should have PENDING, REPLIED, NOT_REQUIRED, etc.
        status_choices = [choice[0] for choice in status_field.choices]
        assert 'PENDING' in status_choices
        assert 'REPLIED' in status_choices
        assert 'NOT_REQUIRED' in status_choices


@pytest.mark.django_db
class TestUserLetterForm:
    # Tests for UserLetterForm - Sector officer letter management

    def test_compulsory_fields_required(self):
        # Invalid: Missing compulsory fields should fail
        form_data = {
            # Missing serial_number, date_received, sender_details, letter_type, accepting_officer_id
            'status': 'PENDING'
        }
        form = UserLetterForm(data=form_data)

        assert not form.is_valid()
        assert 'serial_number' in form.errors
        assert 'date_received' in form.errors
        assert 'sender_details' in form.errors
        assert 'letter_type' in form.errors
        assert 'accepting_officer_id' in form.errors

    def test_replied_status_requires_reply_date(self):
        # Invalid: REPLIED status without replied_at should fail
        form_data = {
            'serial_number': 601,
            'date_received': '2026-06-15',
            'sender_details': 'Reply Test Sender',
            'letter_type': 'Reply Test Type',
            'target_sector': 'GOVERNING',
            'administrated_by': 'CHAIRMAN',
            'accepting_officer_id': 'OFF-001',
            'status': 'REPLIED',
            'replied_at': ''  # Missing reply date
        }
        form = UserLetterForm(data=form_data)

        assert not form.is_valid()
        assert 'replied_at' in form.errors
        assert "Reply Date is compulsory when marking a letter as 'Replied'" in form.errors['replied_at'][0]

    def test_replied_status_with_reply_date_valid(self):
        # Valid: REPLIED status with reply date should pass
        form_data = {
            'serial_number': 602,
            'date_received': '2026-06-15',
            'sender_details': 'Reply Test Sender',
            'letter_type': 'Reply Test Type',
            'target_sector': 'GOVERNING',
            'administrated_by': 'CHAIRMAN',
            'accepting_officer_id': 'OFF-001',
            'status': 'REPLIED',
            'replied_at': '2026-06-20'
        }
        form = UserLetterForm(data=form_data)

        assert form.is_valid(), f"Form should be valid, errors: {form.errors}"
        letter = form.save()
        assert letter.status == 'REPLIED'
        assert letter.replied_at.strftime('%Y-%m-%d') == '2026-06-20'

    def test_not_required_status_clears_reply_date(self):
        # Valid: NOT_REQUIRED status sets replied_at to None
        letter = Letter.objects.create(
            serial_number=701,
            date_received='2026-06-15',
            sender_details='Not Required Sender',
            letter_type='Not Required Type',
            target_sector='GOVERNING',
            administrated_by='CHAIRMAN',
            accepting_officer_id='OFF-001',
            status='PENDING',
            replied_at='2026-06-18'
        )

        form_data = {
            'serial_number': 701,
            'date_received': '2026-06-15',
            'sender_details': 'Not Required Sender',
            'letter_type': 'Not Required Type',
            'target_sector': 'GOVERNING',
            'administrated_by': 'CHAIRMAN',
            'accepting_officer_id': 'OFF-001',
            'status': 'NOT_REQUIRED',
            'replied_at': ''  # Empty
        }
        form = UserLetterForm(data=form_data, instance=letter)

        assert form.is_valid(), f"Form should be valid, errors: {form.errors}"
        updated_letter = form.save()
        assert updated_letter.status == 'NOT_REQUIRED'
        assert updated_letter.replied_at is None

    def test_cannot_modify_serial_number_on_existing(self):
        # Invalid: Cannot change serial number of existing letter
        letter = Letter.objects.create(
            serial_number=801,
            date_received='2026-06-15',
            sender_details='Lock Test Sender',
            letter_type='Lock Test Type',
            target_sector='GOVERNING',
            administrated_by='CHAIRMAN',
            accepting_officer_id='OFF-001'
        )

        form_data = {
            'serial_number': 999,  # Different serial
            'date_received': '2026-06-15',
            'sender_details': 'Lock Test Sender',
            'letter_type': 'Lock Test Type',
            'target_sector': 'GOVERNING',
            'administrated_by': 'CHAIRMAN',
            'accepting_officer_id': 'OFF-001',
            'status': 'PENDING'
        }
        form = UserLetterForm(data=form_data, instance=letter)

        assert not form.is_valid()
        assert 'serial_number' in form.errors
        assert "cannot modify the serial number" in form.errors['serial_number'][0]

    def test_status_choices_limited_for_users(self):
        # Valid: UserLetterForm has limited status choices
        form = UserLetterForm()
        status_choices = [choice[0] for choice in form.fields['status'].choices]

        # Should only have PENDING, REPLIED, NOT_REQUIRED (no DRAFT or others)
        assert 'PENDING' in status_choices
        assert 'REPLIED' in status_choices
        assert 'NOT_REQUIRED' in status_choices
        assert len(status_choices) == 3

    def test_fields_locked_on_existing_letter(self):
        # Valid: Certain fields are locked (readonly) for existing letters
        letter = Letter.objects.create(
            serial_number=901,
            date_received='2026-06-15',
            sender_details='Readonly Test Sender',
            letter_type='Readonly Test Type',
            target_sector='GOVERNING',
            administrated_by='CHAIRMAN',
            accepting_officer_id='OFF-001'
        )

        form = UserLetterForm(instance=letter)

        # These fields should be readonly
        locked_fields = ['serial_number', 'date_received', 'sender_details',
                        'letter_type', 'administrated_by', 'accepting_officer_id']

        for field_name in locked_fields:
            assert 'readonly' in form.fields[field_name].widget.attrs
            assert 'pointer-events: none' in form.fields[field_name].widget.attrs.get('style', '')

    def test_create_new_letter_success(self):
        # Valid: Create new letter with all required fields
        form_data = {
            'serial_number': 1001,
            'date_received': '2026-06-15',
            'sender_details': 'New Letter Sender',
            'letter_type': 'New Letter Type',
            'target_sector': 'GOVERNING',
            'administrated_by': 'CHAIRMAN',
            'accepting_officer_id': 'OFF-001',
            'status': 'PENDING'
        }
        form = UserLetterForm(data=form_data)

        assert form.is_valid(), f"Form should be valid, errors: {form.errors}"
        letter = form.save()
        assert letter.serial_number == 1001
        assert letter.status == 'PENDING'


@pytest.mark.django_db
class TestFormSecurity:
    # Security-focused form tests

    def test_user_form_prevents_staff_creation(self):
        # Security: Regular user form cannot create staff/superuser
        form_data = {
            'username': 'regular_user',
            'first_name': 'Regular',
            'last_name': 'User',
            'sector': 'GOVERNING',
            'new_password': 'SecurePass123!'
        }
        form = UserForm(data=form_data)
        user = form.save()

        assert not user.is_staff
        assert not user.is_superuser

    def test_letter_form_prevents_duplicate_serial_across_sectors(self):
        # Security: Serial numbers must be unique across all sectors
        Letter.objects.create(
            serial_number=1101,
            sender_details='ICT Sender',
            letter_type='ICT Type',
            target_sector='GOVERNING',
            administrated_by='CHAIRMAN',
            accepting_officer_id='OFF-001'
        )

        # Try to create in different sector with same serial
        form_data = {
            'serial_number': 1101,
            'sender_details': 'Finance Sender',
            'letter_type': 'Finance Type',
            'target_sector': 'HEALTH',
            'administrated_by': 'SECRETARY',
            'accepting_officer_id': 'OFF-002',
            'status': 'PENDING'
        }
        form = LetterForm(data=form_data)

        assert not form.is_valid()
        assert "already in use" in form.errors['serial_number'][0]

    def test_multiple_attachments_allowed(self):
        # Valid: Multiple attachments can be added to a letter
        files = {
            'attachment_1': SimpleUploadedFile("file1.pdf", b"content1", content_type="application/pdf"),
            'attachment_2': SimpleUploadedFile("file2.pdf", b"content2", content_type="application/pdf"),
            'attachment_3': SimpleUploadedFile("file3.jpg", b"content3", content_type="image/jpeg"),
        }

        form_data = {
            'serial_number': 1201,
            'sender_details': 'Multi Attachment Sender',
            'letter_type': 'Multi Attachment Type',
            'target_sector': 'GOVERNING',
            'administrated_by': 'CHAIRMAN',
            'accepting_officer_id': 'OFF-001',
            'status': 'PENDING'
        }
        form = LetterForm(data=form_data, files=files)

        assert form.is_valid(), f"Form should be valid, errors: {form.errors}"
        letter = form.save()
        assert letter.attachment_1
        assert letter.attachment_2
        assert letter.attachment_3