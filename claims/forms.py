from django import forms
import json
import csv
import io


class DataUploadForm(forms.Form):
    OPERATION_CHOICES = [
        ('add', 'Add new data (keep existing)'),
        ('overwrite', 'Overwrite all data (delete existing)')
    ]
    
    FILE_TYPE_CHOICES = [
        ('csv', 'CSV File'),
        ('json', 'JSON File')
    ]
    
    operation = forms.ChoiceField(
        choices=OPERATION_CHOICES,
        widget=forms.RadioSelect,
        initial='add',
        help_text="Choose whether to add new data or replace all existing data"
    )
    
    file_type = forms.ChoiceField(
        choices=FILE_TYPE_CHOICES,
        widget=forms.RadioSelect,
        initial='csv',
        help_text="Select the format of your data files"
    )
    
    claims_file = forms.FileField(
        label='Claims Data File',
        help_text='Upload CSV (pipe-delimited) or JSON file with claims data',
        widget=forms.FileInput(attrs={'accept': '.csv,.json'})
    )
    
    claim_details_file = forms.FileField(
        label='Claim Details Data File',
        help_text='Upload CSV (pipe-delimited) or JSON file with claim details data',
        widget=forms.FileInput(attrs={'accept': '.csv,.json'}),
        required=False
    )
    
    def clean_claims_file(self):
        file = self.cleaned_data['claims_file']
        if not file:
            return file
            
        # Reset file pointer
        file.seek(0)
        
        # Check file extension
        file_type = self.cleaned_data.get('file_type', 'csv')
        if file_type == 'csv' and not file.name.lower().endswith('.csv'):
            raise forms.ValidationError('Please upload a CSV file when CSV format is selected.')
        elif file_type == 'json' and not file.name.lower().endswith('.json'):
            raise forms.ValidationError('Please upload a JSON file when JSON format is selected.')
        
        # Validate file content
        try:
            if file_type == 'csv':
                content = file.read().decode('utf-8')
                file.seek(0)  # Reset for later use
                reader = csv.DictReader(io.StringIO(content), delimiter='|')
                headers = reader.fieldnames
                required_headers = ['id', 'patient_name', 'billed_amount', 'paid_amount', 'status', 'insurer_name', 'discharge_date']
                missing_headers = set(required_headers) - set(headers or [])
                if missing_headers:
                    raise forms.ValidationError(f'Missing required columns: {", ".join(missing_headers)}')
            else:  # JSON
                content = file.read().decode('utf-8')
                file.seek(0)  # Reset for later use
                data = json.loads(content)
                if not isinstance(data, list) or not data:
                    raise forms.ValidationError('JSON file must contain a list of claim objects.')
                # Check first item for required fields
                first_item = data[0]
                required_fields = ['id', 'patient_name', 'billed_amount', 'paid_amount', 'status', 'insurer_name', 'discharge_date']
                missing_fields = set(required_fields) - set(first_item.keys())
                if missing_fields:
                    raise forms.ValidationError(f'Missing required fields in JSON: {", ".join(missing_fields)}')
        except json.JSONDecodeError:
            raise forms.ValidationError('Invalid JSON file format.')
        except UnicodeDecodeError:
            raise forms.ValidationError('File encoding error. Please use UTF-8 encoding.')
        except Exception as e:
            raise forms.ValidationError(f'Error validating file: {str(e)}')
        
        return file
    
    def clean_claim_details_file(self):
        file = self.cleaned_data.get('claim_details_file')
        if not file:
            return file
            
        # Reset file pointer
        file.seek(0)
        
        file_type = self.cleaned_data.get('file_type', 'csv')
        
        # Validate file content
        try:
            if file_type == 'csv':
                content = file.read().decode('utf-8')
                file.seek(0)  # Reset for later use
                reader = csv.DictReader(io.StringIO(content), delimiter='|')
                headers = reader.fieldnames
                required_headers = ['claim_id', 'cpt_codes']
                missing_headers = set(required_headers) - set(headers or [])
                if missing_headers:
                    raise forms.ValidationError(f'Missing required columns in details file: {", ".join(missing_headers)}')
            else:  # JSON
                content = file.read().decode('utf-8')
                file.seek(0)  # Reset for later use
                data = json.loads(content)
                if not isinstance(data, list) or not data:
                    raise forms.ValidationError('JSON details file must contain a list of detail objects.')
                # Check first item for required fields
                first_item = data[0]
                required_fields = ['claim_id', 'cpt_codes']
                missing_fields = set(required_fields) - set(first_item.keys())
                if missing_fields:
                    raise forms.ValidationError(f'Missing required fields in details JSON: {", ".join(missing_fields)}')
        except json.JSONDecodeError:
            raise forms.ValidationError('Invalid JSON format in details file.')
        except UnicodeDecodeError:
            raise forms.ValidationError('File encoding error in details file. Please use UTF-8 encoding.')
        except Exception as e:
            raise forms.ValidationError(f'Error validating details file: {str(e)}')
        
        return file
