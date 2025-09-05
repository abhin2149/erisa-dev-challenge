import csv
import json
import io
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import Claim, ClaimDetail

logger = logging.getLogger('claims')


class DataImporter:
    # File size limit: 50MB
    MAX_FILE_SIZE = 50 * 1024 * 1024
    # Maximum rows to process
    MAX_ROWS = 50000
    
    def __init__(self):
        self.results = {
            'claims_created': 0,
            'claims_updated': 0,
            'details_created': 0,
            'details_updated': 0,
            'errors': []
        }
    
    def validate_file(self, file):
        """Validate uploaded file for security and size constraints"""
        if not file:
            raise ValidationError("No file provided")
        
        if file.size > self.MAX_FILE_SIZE:
            raise ValidationError(f"File size exceeds maximum limit of {self.MAX_FILE_SIZE // (1024*1024)}MB")
        
        # Reset file pointer for subsequent operations
        file.seek(0)
        return True
    
    def safe_decimal_conversion(self, value, field_name):
        """Safely convert string to decimal with proper error handling"""
        try:
            # Remove any currency symbols and whitespace
            cleaned_value = str(value).replace('$', '').replace(',', '').strip()
            if not cleaned_value:
                return Decimal('0.00')
            
            decimal_value = Decimal(cleaned_value)
            
            # Check for reasonable bounds (adjust as needed for your use case)
            if decimal_value < 0:
                raise ValueError(f"Negative value not allowed for {field_name}")
            if decimal_value > Decimal('9999999.99'):
                raise ValueError(f"Value too large for {field_name}")
                
            return decimal_value
            
        except (InvalidOperation, ValueError) as e:
            raise ValueError(f"Invalid {field_name}: '{value}' - {str(e)}")
    
    def import_data(self, claims_file, details_file=None, file_type='csv', operation='add'):
        """
        Import claims and details data from uploaded files
        
        Args:
            claims_file: Uploaded claims file
            details_file: Optional uploaded details file
            file_type: 'csv' or 'json'
            operation: 'add' or 'overwrite'
        """
        try:
            # Validate files first
            self.validate_file(claims_file)
            if details_file:
                self.validate_file(details_file)
            
            logger.info(f"Starting data import: file_type={file_type}, operation={operation}")
            
            with transaction.atomic():
                if operation == 'overwrite':
                    logger.warning("Deleting all existing data as requested")
                    # Delete all existing data
                    ClaimDetail.objects.all().delete()
                    Claim.objects.all().delete()
                
                # Import claims
                if file_type == 'csv':
                    self._import_claims_csv(claims_file, operation == 'add')
                    if details_file:
                        self._import_details_csv(details_file, operation == 'add')
                else:  # JSON
                    self._import_claims_json(claims_file, operation == 'add')
                    if details_file:
                        self._import_details_json(details_file, operation == 'add')
                        
            logger.info(f"Import completed: {self.results}")
                        
        except ValidationError as e:
            error_msg = f'Validation failed: {str(e)}'
            self.results['errors'].append(error_msg)
            logger.error(error_msg)
            raise
        except Exception as e:
            error_msg = f'Import failed: {str(e)}'
            self.results['errors'].append(error_msg)
            logger.error(error_msg, exc_info=True)
            raise
        
        return self.results
    
    def _import_claims_csv(self, file, append=True):
        """Import claims from CSV file"""
        file.seek(0)
        content = file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(content), delimiter='|')
        
        row_count = 0
        for row_num, row in enumerate(reader, start=2):
            # Protect against too many rows
            row_count += 1
            if row_count > self.MAX_ROWS:
                error_msg = f"File exceeds maximum allowed rows ({self.MAX_ROWS})"
                self.results['errors'].append(error_msg)
                logger.warning(error_msg)
                break
                
            try:
                claim_id = int(row['id'])
                
                # Validate claim ID is positive
                if claim_id <= 0:
                    raise ValueError(f"Invalid claim ID: {claim_id}")
                
                # Parse date with better error handling
                discharge_date = self._parse_date(row['discharge_date'], f"Row {row_num}")
                
                # Use safe decimal conversion
                billed_amount = self.safe_decimal_conversion(row['billed_amount'], 'billed_amount')
                paid_amount = self.safe_decimal_conversion(row['paid_amount'], 'paid_amount')
                
                # Validate status
                valid_statuses = ['Paid', 'Denied', 'Under Review']
                if row['status'] not in valid_statuses:
                    raise ValueError(f"Invalid status: {row['status']}. Must be one of: {valid_statuses}")
                
                # Validate required fields are not empty
                if not row.get('patient_name', '').strip():
                    raise ValueError("Patient name is required")
                if not row.get('insurer_name', '').strip():
                    raise ValueError("Insurer name is required")
                
                # Create or update claim
                claim, created = Claim.objects.get_or_create(
                    id=claim_id,
                    defaults={
                        'patient_name': row['patient_name'].strip()[:255],  # Truncate to field limit
                        'billed_amount': billed_amount,
                        'paid_amount': paid_amount,
                        'status': row['status'],
                        'insurer_name': row['insurer_name'].strip()[:255],  # Truncate to field limit
                        'discharge_date': discharge_date,
                        'burger_combo_code': row.get('burger_combo_code', '')[:100],  # Truncate to field limit
                    }
                )
                
                if created:
                    self.results['claims_created'] += 1
                elif not append:
                    # Update existing claim
                    claim.patient_name = row['patient_name'].strip()[:255]
                    claim.billed_amount = billed_amount
                    claim.paid_amount = paid_amount
                    claim.status = row['status']
                    claim.insurer_name = row['insurer_name'].strip()[:255]
                    claim.discharge_date = discharge_date
                    claim.burger_combo_code = row.get('burger_combo_code', '')[:100]
                    claim.save()
                    self.results['claims_updated'] += 1
                    
            except Exception as e:
                error_msg = f'Row {row_num}: {str(e)}'
                self.results['errors'].append(error_msg)
                logger.error(error_msg)
    
    def _parse_date(self, date_str, context=""):
        """Parse date string with multiple format support"""
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            # Try other common date formats
            for date_format in ['%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d', '%m-%d-%Y', '%d-%m-%Y']:
                try:
                    return datetime.strptime(date_str, date_format).date()
                except ValueError:
                    continue
            raise ValueError(f"{context} Invalid date format: {date_str}. Expected YYYY-MM-DD or MM/DD/YYYY or DD/MM/YYYY")
    
    def _import_claims_json(self, file, append=True):
        """Import claims from JSON file"""
        file.seek(0)
        content = file.read().decode('utf-8')
        data = json.loads(content)
        
        if len(data) > self.MAX_ROWS:
            error_msg = f"JSON file exceeds maximum allowed rows ({self.MAX_ROWS})"
            self.results['errors'].append(error_msg)
            logger.warning(error_msg)
            data = data[:self.MAX_ROWS]
        
        for i, item in enumerate(data):
            try:
                claim_id = int(item['id'])
                
                # Validate claim ID is positive
                if claim_id <= 0:
                    raise ValueError(f"Invalid claim ID: {claim_id}")
                
                # Parse date with better error handling
                discharge_date = self._parse_date(item['discharge_date'], f"Item {i+1}")
                
                # Use safe decimal conversion
                billed_amount = self.safe_decimal_conversion(item['billed_amount'], 'billed_amount')
                paid_amount = self.safe_decimal_conversion(item['paid_amount'], 'paid_amount')
                
                # Validate status
                valid_statuses = ['Paid', 'Denied', 'Under Review']
                if item['status'] not in valid_statuses:
                    raise ValueError(f"Invalid status: {item['status']}. Must be one of: {valid_statuses}")
                
                # Validate required fields are not empty
                if not item.get('patient_name', '').strip():
                    raise ValueError("Patient name is required")
                if not item.get('insurer_name', '').strip():
                    raise ValueError("Insurer name is required")
                
                # Create or update claim
                claim, created = Claim.objects.get_or_create(
                    id=claim_id,
                    defaults={
                        'patient_name': item['patient_name'].strip()[:255],  # Truncate to field limit
                        'billed_amount': billed_amount,
                        'paid_amount': paid_amount,
                        'status': item['status'],
                        'insurer_name': item['insurer_name'].strip()[:255],  # Truncate to field limit
                        'discharge_date': discharge_date,
                        'burger_combo_code': item.get('burger_combo_code', '')[:100],  # Truncate to field limit
                    }
                )
                
                if created:
                    self.results['claims_created'] += 1
                elif not append:
                    # Update existing claim
                    claim.patient_name = item['patient_name'].strip()[:255]
                    claim.billed_amount = billed_amount
                    claim.paid_amount = paid_amount
                    claim.status = item['status']
                    claim.insurer_name = item['insurer_name'].strip()[:255]
                    claim.discharge_date = discharge_date
                    claim.burger_combo_code = item.get('burger_combo_code', '')[:100]
                    claim.save()
                    self.results['claims_updated'] += 1
                    
            except Exception as e:
                error_msg = f'Item {i+1}: {str(e)}'
                self.results['errors'].append(error_msg)
                logger.error(error_msg)
    
    def _import_details_csv(self, file, append=True):
        """Import claim details from CSV file"""
        file.seek(0)
        content = file.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(content), delimiter='|')
        
        for row_num, row in enumerate(reader, start=2):
            try:
                claim_id = int(row['claim_id'])
                
                try:
                    claim = Claim.objects.get(id=claim_id)
                except Claim.DoesNotExist:
                    self.results['errors'].append(f'Row {row_num}: Claim {claim_id} not found')
                    continue
                
                # Create or update claim detail
                detail, created = ClaimDetail.objects.get_or_create(
                    claim=claim,
                    defaults={
                        'cpt_codes': row['cpt_codes'],
                        'denial_reason': row.get('denial_reason', '') or None,
                    }
                )
                
                if created:
                    self.results['details_created'] += 1
                elif not append:
                    # Update existing detail
                    detail.cpt_codes = row['cpt_codes']
                    detail.denial_reason = row.get('denial_reason', '') or None
                    detail.save()
                    self.results['details_updated'] += 1
                    
            except Exception as e:
                self.results['errors'].append(f'Row {row_num}: {str(e)}')
    
    def _import_details_json(self, file, append=True):
        """Import claim details from JSON file"""
        file.seek(0)
        content = file.read().decode('utf-8')
        data = json.loads(content)
        
        for i, item in enumerate(data):
            try:
                claim_id = int(item['claim_id'])
                
                try:
                    claim = Claim.objects.get(id=claim_id)
                except Claim.DoesNotExist:
                    self.results['errors'].append(f'Item {i+1}: Claim {claim_id} not found')
                    continue
                
                # Create or update claim detail
                detail, created = ClaimDetail.objects.get_or_create(
                    claim=claim,
                    defaults={
                        'cpt_codes': item['cpt_codes'],
                        'denial_reason': item.get('denial_reason', '') or None,
                    }
                )
                
                if created:
                    self.results['details_created'] += 1
                elif not append:
                    # Update existing detail
                    detail.cpt_codes = item['cpt_codes']
                    detail.denial_reason = item.get('denial_reason', '') or None
                    detail.save()
                    self.results['details_updated'] += 1
                    
            except Exception as e:
                self.results['errors'].append(f'Item {i+1}: {str(e)}')


def export_claims_to_json():
    """Export all claims data to JSON format"""
    claims_data = []
    details_data = []
    
    for claim in Claim.objects.all():
        claim_dict = {
            'id': claim.id,
            'patient_name': claim.patient_name,
            'billed_amount': str(claim.billed_amount),
            'paid_amount': str(claim.paid_amount),
            'status': claim.status,
            'insurer_name': claim.insurer_name,
            'discharge_date': claim.discharge_date.strftime('%Y-%m-%d'),
            'burger_combo_code': claim.burger_combo_code or '',
        }
        claims_data.append(claim_dict)
        
        # Add details if they exist
        if hasattr(claim, 'details'):
            detail_dict = {
                'claim_id': claim.id,
                'cpt_codes': claim.details.cpt_codes,
                'denial_reason': claim.details.denial_reason or '',
            }
            details_data.append(detail_dict)
    
    return claims_data, details_data


def export_claims_to_csv():
    """Export all claims data to CSV format"""
    import io
    
    # Export claims
    claims_output = io.StringIO()
    claims_fieldnames = ['id', 'patient_name', 'billed_amount', 'paid_amount', 'status', 'insurer_name', 'discharge_date', 'burger_combo_code']
    claims_writer = csv.DictWriter(claims_output, fieldnames=claims_fieldnames, delimiter='|')
    claims_writer.writeheader()
    
    for claim in Claim.objects.all():
        claims_writer.writerow({
            'id': claim.id,
            'patient_name': claim.patient_name,
            'billed_amount': str(claim.billed_amount),
            'paid_amount': str(claim.paid_amount),
            'status': claim.status,
            'insurer_name': claim.insurer_name,
            'discharge_date': claim.discharge_date.strftime('%Y-%m-%d'),
            'burger_combo_code': claim.burger_combo_code or '',
        })
    
    # Export details
    details_output = io.StringIO()
    details_fieldnames = ['claim_id', 'cpt_codes', 'denial_reason']
    details_writer = csv.DictWriter(details_output, fieldnames=details_fieldnames, delimiter='|')
    details_writer.writeheader()
    
    for detail in ClaimDetail.objects.select_related('claim'):
        details_writer.writerow({
            'claim_id': detail.claim.id,
            'cpt_codes': detail.cpt_codes,
            'denial_reason': detail.denial_reason or '',
        })
    
    return claims_output.getvalue(), details_output.getvalue()
