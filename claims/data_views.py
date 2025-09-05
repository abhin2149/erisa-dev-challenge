from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import HttpResponse
from datetime import datetime
import json
from .models import Claim, ClaimDetail, Flag, Note
from .forms import DataUploadForm
from .utils import DataImporter, export_claims_to_json, export_claims_to_csv


@staff_member_required
def data_upload_view(request):
    """Handle data upload form"""
    if request.method == 'POST':
        form = DataUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Get form data
                operation = form.cleaned_data['operation']
                file_type = form.cleaned_data['file_type']
                claims_file = form.cleaned_data['claims_file']
                details_file = form.cleaned_data.get('claim_details_file')
                
                # Import data
                importer = DataImporter()
                results = importer.import_data(
                    claims_file=claims_file,
                    details_file=details_file,
                    file_type=file_type,
                    operation=operation
                )
                
                # Show success message with results
                success_msg = (
                    f"Data import completed successfully! "
                    f"Claims: {results['claims_created']} created, {results['claims_updated']} updated. "
                    f"Details: {results['details_created']} created, {results['details_updated']} updated."
                )
                
                if results['errors']:
                    success_msg += f" {len(results['errors'])} errors occurred."
                    for error in results['errors'][:5]:  # Show first 5 errors
                        messages.warning(request, f"Error: {error}")
                    if len(results['errors']) > 5:
                        messages.warning(request, f"... and {len(results['errors']) - 5} more errors.")
                
                messages.success(request, success_msg)
                return redirect('data_admin_upload')
                
            except Exception as e:
                messages.error(request, f"Import failed: {str(e)}")
    else:
        form = DataUploadForm()
    
    # Get current data statistics
    claims_count = Claim.objects.count()
    details_count = ClaimDetail.objects.count()
    flags_count = Flag.objects.count()
    notes_count = Note.objects.count()
    
    context = {
        'form': form,
        'title': 'Upload Claims Data',
        'opts': {'app_label': 'claims'},
        'has_permission': True,
        'claims_count': claims_count,
        'details_count': details_count,
        'flags_count': flags_count,
        'notes_count': notes_count,
        'site_header': 'Claims Data Management',
        'site_title': 'Claims Admin',
    }
    return render(request, 'admin/data_upload.html', context)


@staff_member_required
def data_export_view(request):
    """Handle data export"""
    export_format = request.GET.get('format', 'json')
    
    if export_format == 'json':
        claims_data, details_data = export_claims_to_json()
        
        export_data = {
            'claims': claims_data,
            'claim_details': details_data,
            'export_date': str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            'total_claims': len(claims_data),
            'total_details': len(details_data)
        }
        
        response = HttpResponse(
            json.dumps(export_data, indent=2),
            content_type='application/json'
        )
        response['Content-Disposition'] = 'attachment; filename="claims_export.json"'
        return response
    
    else:  # CSV
        claims_csv, details_csv = export_claims_to_csv()
        
        if request.GET.get('type') == 'details':
            response = HttpResponse(details_csv, content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="claim_details_export.csv"'
        else:
            response = HttpResponse(claims_csv, content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="claims_export.csv"'
        
        return response


@staff_member_required
def data_management_dashboard(request):
    """Data management dashboard view"""
    # Get current data statistics
    claims_count = Claim.objects.count()
    details_count = ClaimDetail.objects.count()
    flags_count = Flag.objects.count()
    notes_count = Note.objects.count()
    
    context = {
        'title': 'Claims Data Management',
        'claims_count': claims_count,
        'details_count': details_count,
        'flags_count': flags_count,
        'notes_count': notes_count,
        'site_header': 'Claims Data Management',
        'site_title': 'Claims Admin',
        'has_permission': True,
    }
    return render(request, 'admin/data_dashboard.html', context)
