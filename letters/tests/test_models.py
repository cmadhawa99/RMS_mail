"""
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Model Tests
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Tests for all model classes: Letter, SectorProfile, LetterImage, BackupSettings
and the process_scanned_image utility function.

These tests ensure:
- Model field validation
- Business logic in save() methods
- Relationships between models
- String representations
- Default values and choices
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from datetime import date
import io
from PIL import Image

from letters.models import (
    Letter,
    SectorProfile,
    LetterImage,
    BackupSettings,
    process_scanned_image,
    OFFICER_CHOICES,
    SECTOR_CHOICES,
    STATUS_CHOICES,
)


class TestOfficerChoices(TestCase):
    # Test that officer choices are properly defined

    def test_officer_choices_count(self):
        # Should have 4 officer choices
        self.assertEqual(len(OFFICER_CHOICES), 4)

    def test_officer_choices_values(self):
        # Should contain expected officer roles
        choice_values = [choice[0] for choice in OFFICER_CHOICES]
        self.assertIn('CHAIRMAN', choice_values)
        self.assertIn('SECRETARY', choice_values)
        self.assertIn('CHIEF MANAGEMENT OFFICER', choice_values)
        self.assertIn('HEAD OF SECTION', choice_values)


class TestSectorChoices(TestCase):
    # Test that sector choices are properly defined

    def test_sector_choices_count(self):
        # Should have 5 sector choices
        self.assertEqual(len(SECTOR_CHOICES), 5)

    def test_sector_choices_values(self):
        # Should contain expected sectors
        choice_values = [choice[0] for choice in SECTOR_CHOICES]
        self.assertIn('GOVERNING', choice_values)
        self.assertIn('HEALTH', choice_values)
        self.assertIn('DEVELOPMENT', choice_values)
        self.assertIn('INCOME', choice_values)
        self.assertIn('ACCOUNTS', choice_values)


class TestStatusChoices(TestCase):
    # Test that status choices are properly defined

    def test_status_choices_count(self):
        # Should have 4 status choices
        self.assertEqual(len(STATUS_CHOICES), 4)

    def test_status_choices_values(self):
        # Should contain expected statuses
        choice_values = [choice[0] for choice in STATUS_CHOICES]
        self.assertIn('PENDING', choice_values)
        self.assertIn('REPLIED', choice_values)
        self.assertIn('NOT_REQUIRED', choice_values)
        self.assertIn('ADMIN_UPDATED', choice_values)


class TestLetterModel(TestCase):
    # Test the Letter model functionality

    def setUp(self):
        # Create a sample letter for testing
        self.letter = Letter.objects.create(
            serial_number=1001,
            date_received=date(2024, 1, 15),
            sender_details="ඩී.යූ.සී.කිරිබණ්ඩා, කහටගස්දෙනිය",
            letter_type="ආදායම් බදු ගෙවීම - සල්ලි ගස්වලින් කඩනවා යැයි සිතන මහත්වරුන්ටයි",
            accepting_officer_id="ආ/67",
            target_sector='HEALTH',
            administrated_by='SECRETARY',
            status='PENDING',
            created_by="ADMIN",
        )

    def test_letter_creation(self):
       # Should create a letter with required fields
        self.assertEqual(self.letter.serial_number, 1001)
        self.assertEqual(self.letter.target_sector, 'HEALTH')
        self.assertEqual(self.letter.status, 'PENDING')

    def test_letter_string_representation(self):
        # Should return formatted string with serial number and sector
        expected = "1001 (Health Section)"
        self.assertEqual(str(self.letter), expected)

    def test_letter_default_status(self):
        # Should default to PENDING status
        letter = Letter.objects.create(serial_number=1002)
        self.assertEqual(letter.status, 'PENDING')

    def test_letter_unique_serial_number(self):
        # Should not allow duplicate serial numbers
        with self.assertRaises(Exception):
            Letter.objects.create(serial_number=1001)

    def test_letter_ordering(self):
        # Should order letters by serial_number
        Letter.objects.create(serial_number=999)
        Letter.objects.create(serial_number=1003)

        letters = list(Letter.objects.all())
        self.assertEqual(letters[0].serial_number, 999)
        self.assertEqual(letters[1].serial_number, 1001)
        self.assertEqual(letters[2].serial_number, 1003)

    def test_letter_get_target_sector_display(self):
        # Should return human-readable sector name
        self.assertEqual(self.letter.get_target_sector_display(), 'Health Section')

    def test_letter_get_administrated_by_display(self):
        # Should return human-readable officer name
        self.assertEqual(self.letter.get_administrated_by_display(), 'Secretary')

    def test_letter_optional_fields(self):
        # Should allow optional fields to be null or blank
        letter = Letter.objects.create(serial_number=1002)
        self.assertIsNone(letter.date_received)
        self.assertIsNone(letter.sender_details)
        self.assertIsNone(letter.letter_type)
        self.assertIsNone(letter.accepting_officer_id)
        self.assertIsNone(letter.target_sector)
        self.assertIsNone(letter.administrated_by)

    def test_letter_replied_at_nullable(self):
        # Should allow replied_at to be null initially
        self.assertIsNone(self.letter.replied_at)

    def test_letter_created_at_auto(self):
        # Should automatically set created_at on creation
        self.assertIsNotNone(self.letter.created_at)


class TestSectorProfileModel(TestCase):
    # Test the SectorProfile model functionality

    def setUp(self):
        # Create a test user and sector profile
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.profile = SectorProfile.objects.create(
            user=self.user,
            sector='HEALTH'
        )

    def test_sector_profile_creation(self):
        # Should create a sector profile linked to a user
        self.assertEqual(self.profile.user.username, 'testuser')
        self.assertEqual(self.profile.sector, 'HEALTH')

    def test_sector_profile_string_representation(self):
        # Should return formatted string with username and sector
        expected = "testuser - Health Section"
        self.assertEqual(str(self.profile), expected)

    def test_sector_profile_cascade_delete(self):
        # Should delete profile when user is deleted
        user_id = self.user.id
        self.user.delete()
        self.assertFalse(SectorProfile.objects.filter(user_id=user_id).exists())

    def test_sector_profile_one_to_one(self):
        # Should not allow multiple profiles for same user
        with self.assertRaises(Exception):
            SectorProfile.objects.create(user=self.user, sector='DEVELOPMENT')

    def test_all_sector_choices_valid(self):
        # Should accept all valid sector choices
        for sector_code, _ in SECTOR_CHOICES:
            user = User.objects.create_user(username=f'user_{sector_code}', password='pass')
            profile = SectorProfile.objects.create(user=user, sector=sector_code)
            self.assertEqual(profile.sector, sector_code)
            profile.delete()
            user.delete()


class TestLetterImageModel(TestCase):
    # Test the LetterImage model functionality

    def setUp(self):
        # Create a letter and image for testing
        self.letter = Letter.objects.create(serial_number=2001)

        # Create a simple test image
        img_data = io.BytesIO()
        test_image = Image.new('RGB', (100, 100), color='red')
        test_image.save(img_data, format='JPEG')
        img_data.seek(0)

        self.image_file = SimpleUploadedFile(
            name='test_page.jpg',
            content=img_data.read(),
            content_type='image/jpeg'
        )

    def test_letter_image_creation(self):
        # Should create a letter image linked to a letter
        letter_image = LetterImage.objects.create(
            letter=self.letter,
            image=self.image_file
        )
        self.assertEqual(letter_image.letter, self.letter)
        self.assertIsNotNone(letter_image.image)

    def test_letter_image_string_representation(self):
        # Should return formatted string with letter serial number
        letter_image = LetterImage.objects.create(
            letter=self.letter,
            image=self.image_file
        )
        expected = "Page for Letter #2001"
        self.assertEqual(str(letter_image), expected)

    def test_letter_image_cascade_delete(self):
        # Should delete images when letter is deleted
        letter_image = LetterImage.objects.create(
            letter=self.letter,
            image=self.image_file
        )
        letter_id = self.letter.id

        self.letter.delete()

        self.assertFalse(LetterImage.objects.filter(id=letter_image.id).exists())

    def test_letter_image_multiple_pages(self):
        # Should allow multiple images for a single letter
        img_data = io.BytesIO()
        test_image = Image.new('RGB', (100, 100), color='blue')
        test_image.save(img_data, format='JPEG')
        img_data.seek(0)

        image_file_2 = SimpleUploadedFile(
            name='test_page2.jpg',
            content=img_data.read(),
            content_type='image/jpeg'
        )

        LetterImage.objects.create(letter=self.letter, image=self.image_file)
        LetterImage.objects.create(letter=self.letter, image=image_file_2)

        self.assertEqual(self.letter.images.count(), 2)

    def test_letter_image_created_at_auto(self):
        # Should automatically set created_at on creation
        letter_image = LetterImage.objects.create(
            letter=self.letter,
            image=self.image_file
        )
        self.assertIsNotNone(letter_image.created_at)


class TestBackupSettingsModel(TestCase):
    # Test the BackupSettings model functionality

    def test_backup_settings_creation(self):
        # Should create backup settings with defaults
        settings = BackupSettings.objects.create()
        self.assertFalse(settings.auto_backup_enabled)
        self.assertIsNone(settings.last_auto_backup_date)

    def test_backup_settings_defaults(self):
        # Should have correct default values
        settings = BackupSettings.objects.create()
        self.assertEqual(settings.auto_backup_enabled, False)

    def test_backup_settings_update(self):
        # Should allow updating backup settings
        settings = BackupSettings.objects.create()
        settings.auto_backup_enabled = True
        settings.last_auto_backup_date = date(2024, 1, 15)
        settings.save()

        settings.refresh_from_db()
        self.assertTrue(settings.auto_backup_enabled)
        self.assertEqual(settings.last_auto_backup_date, date(2024, 1, 15))

    def test_backup_settings_verbose_name_plural(self):
        # Should have correct verbose name plural
        self.assertEqual(
            BackupSettings._meta.verbose_name_plural,
            "Backup Settings"
        )


class TestProcessScannedImage(TestCase):
    # Test the process_scanned_image utility function"""

    def test_process_none_image(self):
        # Should return None when given None
        result = process_scanned_image(None, 'test_field')
        self.assertIsNone(result)

    def test_process_valid_image(self):
        # Should process a valid image and return optimized version
        # Create a test image
        img_data = io.BytesIO()
        test_image = Image.new('RGB', (800, 600), color='green')
        test_image.save(img_data, format='JPEG')
        img_data.seek(0)

        # Wrap in a file-like object
        from django.core.files.base import ContentFile
        image_file = ContentFile(img_data.read(), name='test.jpg')

        # Process the image
        result = process_scanned_image(image_file, 'attachment_1')

        # Verify result is a file-like object
        self.assertIsNotNone(result)
        self.assertEqual(result.name, 'attachment_1.jpg')
        self.assertEqual(result.content_type, 'image/jpeg')

    def test_process_image_grayscale(self):
        # Should convert image to grayscale
        img_data = io.BytesIO()
        test_image = Image.new('RGB', (400, 300), color='red')
        test_image.save(img_data, format='JPEG')
        img_data.seek(0)

        from django.core.files.base import ContentFile
        image_file = ContentFile(img_data.read(), name='test.jpg')

        result = process_scanned_image(image_file, 'attachment_1')

        # Load the processed image to verify it's grayscale
        processed_img = Image.open(result)
        self.assertEqual(processed_img.mode, 'L')  # 'L' mode is grayscale

    def test_process_image_size_reduction(self):
        # Should reduce image size if exceeds max dimensions
        # Create a large image
        img_data = io.BytesIO()
        test_image = Image.new('RGB', (2000, 1500), color='blue')
        test_image.save(img_data, format='JPEG')
        img_data.seek(0)

        from django.core.files.base import ContentFile
        image_file = ContentFile(img_data.read(), name='test.jpg')

        result = process_scanned_image(image_file, 'attachment_1')

        # Verify dimensions are within limits
        processed_img = Image.open(result)
        self.assertLessEqual(processed_img.width, 1200)
        self.assertLessEqual(processed_img.height, 1600)

    def test_process_image_preserves_aspect_ratio(self):
        # Should preserve aspect ratio when resizing
        img_data = io.BytesIO()
        test_image = Image.new('RGB', (2400, 1200), color='yellow')
        test_image.save(img_data, format='JPEG')
        img_data.seek(0)

        from django.core.files.base import ContentFile
        image_file = ContentFile(img_data.read(), name='test.jpg')

        result = process_scanned_image(image_file, 'attachment_1')

        processed_img = Image.open(result)
        # Original aspect ratio is 2:1, should be preserved
        self.assertAlmostEqual(
            processed_img.width / processed_img.height,
            2.0,
            places=1
        )