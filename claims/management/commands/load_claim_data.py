import csv
import os
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from claims.models import Claim, ClaimDetail


class Command(BaseCommand):
    help = 'Load claims data from CSV files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--claims-file',
            type=str,
            default='claim_list_data.csv',
            help='Path to the claims CSV file',
        )
        parser.add_argument(
            '--details-file',
            type=str,
            default='claim_detail_data.csv',
            help='Path to the claim details CSV file',
        )
        parser.add_argument(
            '--append',
            action='store_true',
            help='Append new records without deleting existing ones',
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            help='Delete all existing claims data before importing',
        )

    def handle(self, *args, **options):
        claims_file = options['claims_file']
        details_file = options['details_file']
        append = options['append']
        overwrite = options['overwrite']

        # Validate file existence
        if not os.path.exists(claims_file):
            raise CommandError(f'Claims file "{claims_file}" does not exist.')
        
        if not os.path.exists(details_file):
            raise CommandError(f'Details file "{details_file}" does not exist.')

        try:
            with transaction.atomic():
                if overwrite:
                    self.stdout.write('Deleting existing claims data...')
                    ClaimDetail.objects.all().delete()
                    Claim.objects.all().delete()
                    self.stdout.write(self.style.SUCCESS('Existing data deleted.'))

                # Load claims data
                self.stdout.write('Loading claims data...')
                claims_loaded = self.load_claims(claims_file, append)
                
                # Load claim details
                self.stdout.write('Loading claim details...')
                details_loaded = self.load_claim_details(details_file, append)
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully loaded {claims_loaded} claims and {details_loaded} claim details.'
                    )
                )

        except Exception as e:
            raise CommandError(f'Error loading data: {str(e)}')

    def load_claims(self, file_path, append=False):
        loaded_count = 0
        
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file, delimiter='|')
            
            for row in reader:
                claim_id = int(row['id'])
                
                # Skip if not appending and claim exists
                if not append and Claim.objects.filter(id=claim_id).exists():
                    continue
                
                # Parse date
                discharge_date = datetime.strptime(row['discharge_date'], '%Y-%m-%d').date()
                
                # Create or update claim
                claim, created = Claim.objects.get_or_create(
                    id=claim_id,
                    defaults={
                        'patient_name': row['patient_name'],
                        'billed_amount': float(row['billed_amount']),
                        'paid_amount': float(row['paid_amount']),
                        'status': row['status'],
                        'insurer_name': row['insurer_name'],
                        'discharge_date': discharge_date,
                        'burger_combo_code': row.get('burger_combo_code', ''),
                    }
                )
                
                if created or append:
                    loaded_count += 1
                    if loaded_count % 100 == 0:
                        self.stdout.write(f'Loaded {loaded_count} claims...')
        
        return loaded_count

    def load_claim_details(self, file_path, append=False):
        loaded_count = 0
        
        with open(file_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file, delimiter='|')
            
            for row in reader:
                claim_id = int(row['claim_id'])
                
                try:
                    claim = Claim.objects.get(id=claim_id)
                except Claim.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'Claim {claim_id} not found, skipping detail record.')
                    )
                    continue
                
                # Skip if not appending and detail exists
                if not append and hasattr(claim, 'details'):
                    continue
                
                # Create or update claim detail
                detail, created = ClaimDetail.objects.get_or_create(
                    claim=claim,
                    defaults={
                        'cpt_codes': row['cpt_codes'],
                        'denial_reason': row.get('denial_reason', '') or None,
                    }
                )
                
                if created or append:
                    loaded_count += 1
                    if loaded_count % 100 == 0:
                        self.stdout.write(f'Loaded {loaded_count} claim details...')
        
        return loaded_count
