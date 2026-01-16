import random
from faker import Faker
from faker.providers import BaseProvider
from django.core.management.base import BaseCommand
from letters.models import Letter, SECTOR_CHOICES, OFFICER_CHOICES


# 1. Define a Custom Provider for Sinhala Data
class SinhalaProvider(BaseProvider):
    """
    A custom provider to generate Sinhala names, cities, and addresses.
    """

    def sinhala_name(self):
        first_names = [
            'කමල්', 'නිමල්', 'සුනිල්', 'අමර', 'නයනා', 'චම්පා',
            'රුවන්', 'කුමාර', 'මලිත්', 'සමන්', 'දීපිකා', 'කාන්ති'
        ]
        last_names = [
            'පෙරේරා', 'සිල්වා', 'ප්‍රනාන්දු', 'දිසානායක', 'බණ්ඩාර',
            'ගුණවර්ධන', 'විජේසිංහ', 'කරුණාරත්න', 'රාජපක්ෂ', 'ජයවර්ධන'
        ]
        return f"{self.random_element(first_names)} {self.random_element(last_names)}"

    def sinhala_city(self):
        cities = [
            'මැටිහක්වල', 'හුණුවල - උතුර', 'හුණුවල - දකුණ', 'උඩවෙල', 'උඩරන්වල', 'ගල්කන්ද',
            'පරගහමඩිත්ත', 'මල්මිකන්ද', 'මීගහවෙල', 'හත්තැල්ල', 'දන්දෙණිය'
        ]
        return self.random_element(cities)

    def sinhala_address(self):
        # Generates a simple Sinhala address string
        street_no = self.random_int(min=1, max=999)
        streets = ['පන්සල පාර', 'වෙල පාර', 'පන්සල පාර', 'බෝ ගහ මාවත', 'සමූපකාර මාවත']
        city = self.sinhala_city()
        return f"අංක {street_no}, {self.random_element(streets)}, {city}"


class Command(BaseCommand):
    help = 'Populates the database with random letters for testing'

    def add_arguments(self, parser):
        parser.add_argument('count', type=int, help='The number of letters to create')

    def handle(self, *args, **kwargs):
        count = kwargs['count']

        # 2. Initialize Faker (Default English)
        fake = Faker()

        # 3. Add our Custom Sinhala Provider
        fake.add_provider(SinhalaProvider)

        # Get choices from models
        sectors = [choice[0] for choice in SECTOR_CHOICES]
        officers = [choice[0] for choice in OFFICER_CHOICES]

        # Sinhala Letter Types
        letter_types = [
            'පැමිණිල්ල',  # Complaint
            'සංවර්ධන ඉල්ලීම',  # Development Request
            'බදු විමසීම්',  # Tax Inquiry
            'බලපත්‍ර අයදුම්පත',  # Permit Application
            'සාමාන්‍ය විමසීම'  # General Query
        ]

        self.stdout.write(f"Generating {count} random Sinhala letters...")

        for i in range(count):
            serial = f"2024/{random.choice(['A', 'B', 'C', 'D'])}/{fake.unique.random_number(digits=6)}"

            Letter.objects.create(
                serial_number=serial,
                date_received=fake.date_between(start_date='-1y', end_date='today'),

                # 4. Use the custom methods we defined above
                sender_name=fake.sinhala_name(),
                sender_address=fake.sinhala_address(),

                letter_type=random.choice(letter_types),
                accepting_officer_id=f"OFF-{random.randint(100, 999)}",
                target_sector=random.choice(sectors),
                administrated_by=random.choice(officers),
                is_replied=random.choice([True, False, False])
            )

        self.stdout.write(self.style.SUCCESS(f'Successfully added {count} Sinhala letters to the database!'))