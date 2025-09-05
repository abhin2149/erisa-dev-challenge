"""
Management command to set up production data on Railway deployment
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.management import call_command
import os

User = get_user_model()

class Command(BaseCommand):
    help = 'Set up production database with initial data'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Setting up production database...'))
        
        # Create superuser if it doesn't exist
        if not User.objects.filter(username='admin').exists():
            self.stdout.write('Creating admin user...')
            User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123'  # Change this in production!
            )
            self.stdout.write(self.style.SUCCESS('Admin user created: admin/admin123'))
        else:
            self.stdout.write('Admin user already exists')
            
        # Create test user if it doesn't exist
        if not User.objects.filter(username='testuser').exists():
            self.stdout.write('Creating test user...')
            User.objects.create_user(
                username='testuser',
                email='test@example.com', 
                password='testpass'
            )
            self.stdout.write(self.style.SUCCESS('Test user created: testuser/testpass'))
        else:
            self.stdout.write('Test user already exists')

        # Load sample data if CSV files exist
        csv_files = ['production_sample_data.csv', 'claim_list_data.csv', 'claims_data.csv']
        for csv_file in csv_files:
            if os.path.exists(csv_file):
                self.stdout.write(f'Loading data from {csv_file}...')
                try:
                    call_command('load_claim_data', csv_file)
                    self.stdout.write(self.style.SUCCESS(f'Successfully loaded {csv_file}'))
                    break
                except Exception as e:
                    self.stdout.write(f'Could not load {csv_file}: {e}')
        
        self.stdout.write(self.style.SUCCESS('Production setup complete!'))
