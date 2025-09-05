import logging
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, Http404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q, Sum, Count, Avg, F
from django.db import DatabaseError, transaction
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib import messages
from django.shortcuts import redirect
from django.core.exceptions import ValidationError, PermissionDenied
from .models import Claim, ClaimDetail, Flag, Note

logger = logging.getLogger('claims')


def is_admin_user(user):
    """Check if user is admin/superuser"""
    return user.is_authenticated and (user.is_superuser or user.is_staff)


@login_required
def claims_list(request):
    """Main claims list view with search, filter, and pagination functionality"""
    try:
        logger.debug(f"Claims list requested by user {request.user.username}")
        
        claims = Claim.objects.select_related('details').prefetch_related('flags', 'notes')
        
        # Search functionality with input validation
        search_query = request.GET.get('search', '').strip()
        if len(search_query) > 200:  # Prevent overly long search queries
            search_query = search_query[:200]
            messages.warning(request, "Search query was truncated to 200 characters")
        
        if search_query:
            claims = claims.filter(
                Q(patient_name__icontains=search_query) |
                Q(insurer_name__icontains=search_query)
            )
        
        # Filter by status with validation
        status_filter = request.GET.get('status', '')
        valid_statuses = ['Paid', 'Denied', 'Under Review']
        if status_filter and status_filter not in valid_statuses:
            logger.warning(f"Invalid status filter attempted: {status_filter}")
            status_filter = ''
        
        if status_filter:
            claims = claims.filter(status=status_filter)
        
        # Order by claim ID descending
        claims = claims.order_by('-id')
        
        # Pagination with validation
        page_size = request.GET.get('page_size', '10')
        try:
            page_size = int(page_size)
            if page_size not in [10, 20, 50]:
                page_size = 10
        except (ValueError, TypeError):
            logger.warning(f"Invalid page_size parameter: {page_size}")
            page_size = 10
        
        paginator = Paginator(claims, page_size)
        page = request.GET.get('page', 1)
        
        try:
            claims_page = paginator.page(page)
        except PageNotAnInteger:
            logger.warning(f"Invalid page number: {page}")
            claims_page = paginator.page(1)
        except EmptyPage:
            logger.warning(f"Empty page requested: {page}")
            claims_page = paginator.page(paginator.num_pages)
        
        # For HTMX requests, return only the table content (rows + pagination)
        if request.headers.get('HX-Request'):
            return render(request, 'claims/partials/claims_table_content.html', {
                'claims': claims_page,
                'search_query': search_query,
                'status_filter': status_filter,
                'page_size': page_size,
            })
        
        # Get available statuses for filter dropdown
        status_choices = Claim.status_choices
        
        context = {
            'claims': claims_page,
            'search_query': search_query,
            'status_filter': status_filter,
            'status_choices': status_choices,
            'page_size': page_size,
        }
        
        return render(request, 'claims/claims_list.html', context)
        
    except DatabaseError as e:
        logger.error(f"Database error in claims_list: {str(e)}", exc_info=True)
        messages.error(request, "Database error occurred. Please try again.")
        return render(request, 'claims/claims_list.html', {
            'claims': [],
            'search_query': '',
            'status_filter': '',
            'status_choices': Claim.status_choices,
            'page_size': 10,
        })
    except Exception as e:
        logger.error(f"Unexpected error in claims_list: {str(e)}", exc_info=True)
        messages.error(request, "An unexpected error occurred. Please try again.")
        return render(request, 'claims/claims_list.html', {
            'claims': [],
            'search_query': '',
            'status_filter': '',
            'status_choices': Claim.status_choices,
            'page_size': 10,
        })


@login_required
def claim_detail(request, claim_id):
    """HTMX view for claim details"""
    try:
        # Validate claim_id parameter
        try:
            claim_id = int(claim_id)
            if claim_id <= 0:
                raise ValueError("Invalid claim ID")
        except (ValueError, TypeError):
            logger.warning(f"Invalid claim_id parameter: {claim_id}")
            raise Http404("Invalid claim ID")
        
        logger.debug(f"Fetching claim detail for ID {claim_id} by user {request.user.username}")
        
        try:
            claim = get_object_or_404(Claim, id=claim_id)
        except Claim.DoesNotExist:
            logger.info(f"Claim {claim_id} not found")
            raise Http404("Claim not found")
        
        try:
            claim_details = claim.details
        except ClaimDetail.DoesNotExist:
            logger.debug(f"No details found for claim {claim_id}")
            claim_details = None
        except Exception as e:
            logger.error(f"Error fetching claim details for {claim_id}: {str(e)}")
            claim_details = None
        
        # Get notes and flags with proper error handling
        try:
            notes = claim.notes.select_related('user').order_by('-created_at')
            flags = claim.flags.select_related('user').order_by('-created_at')
        except DatabaseError as e:
            logger.error(f"Database error fetching notes/flags for claim {claim_id}: {str(e)}")
            notes = Note.objects.none()
            flags = Flag.objects.none()
        
        # Check if current user has flagged this claim
        try:
            user_has_flagged = flags.filter(user=request.user).exists() if request.user.is_authenticated else False
        except DatabaseError as e:
            logger.error(f"Error checking user flags for claim {claim_id}: {str(e)}")
            user_has_flagged = False
        
        context = {
            'claim': claim,
            'claim_details': claim_details,
            'notes': notes,
            'flags': flags,
            'user_has_flagged': user_has_flagged,
        }
        
        return render(request, 'claims/partials/claim_detail.html', context)
        
    except Http404:
        raise  # Re-raise 404 errors
    except DatabaseError as e:
        logger.error(f"Database error in claim_detail for ID {claim_id}: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'Database error occurred'}, status=500)
    except Exception as e:
        logger.error(f"Unexpected error in claim_detail for ID {claim_id}: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)


@login_required
@require_http_methods(["POST"])
def flag_claim(request, claim_id):
    """HTMX view to flag a claim"""
    try:
        # Validate claim_id parameter
        try:
            claim_id = int(claim_id)
            if claim_id <= 0:
                raise ValueError("Invalid claim ID")
        except (ValueError, TypeError):
            logger.warning(f"Invalid claim_id parameter in flag_claim: {claim_id}")
            return JsonResponse({'error': 'Invalid claim ID'}, status=400)
        
        logger.info(f"User {request.user.username} attempting to flag claim {claim_id}")
        
        try:
            claim = get_object_or_404(Claim, id=claim_id)
        except Claim.DoesNotExist:
            logger.info(f"Claim {claim_id} not found for flagging")
            return JsonResponse({'error': 'Claim not found'}, status=404)
        
        # Create flag if it doesn't exist with transaction safety
        try:
            with transaction.atomic():
                flag, created = Flag.objects.get_or_create(
                    claim=claim,
                    user=request.user,
                    defaults={'reason': 'Flagged for review'}
                )
            
            if created:
                logger.info(f"Claim {claim_id} flagged by user {request.user.username}")
            else:
                logger.debug(f"Claim {claim_id} already flagged by user {request.user.username}")
                
        except DatabaseError as e:
            logger.error(f"Database error flagging claim {claim_id}: {str(e)}", exc_info=True)
            return JsonResponse({'error': 'Database error occurred'}, status=500)
        
        # Get updated notes and annotations with error handling
        try:
            notes = claim.notes.select_related('user').order_by('-created_at')
            flags = claim.flags.select_related('user').order_by('-created_at')
        except DatabaseError as e:
            logger.error(f"Database error fetching notes/flags after flagging claim {claim_id}: {str(e)}")
            notes = Note.objects.none()
            flags = Flag.objects.none()
        
        user_has_flagged = True
        
        context = {
            'claim': claim,
            'notes': notes,
            'flags': flags,
            'user_has_flagged': user_has_flagged,
            'flag_created': created,
        }
        
        return render(request, 'claims/partials/notes_annotations.html', context)
        
    except Exception as e:
        logger.error(f"Unexpected error in flag_claim for ID {claim_id}: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)


@login_required
@require_http_methods(["POST"])
def add_note(request, claim_id):
    """HTMX view to add a note to a claim"""
    try:
        # Validate claim_id parameter
        try:
            claim_id = int(claim_id)
            if claim_id <= 0:
                raise ValueError("Invalid claim ID")
        except (ValueError, TypeError):
            logger.warning(f"Invalid claim_id parameter in add_note: {claim_id}")
            return JsonResponse({'error': 'Invalid claim ID'}, status=400)
        
        logger.debug(f"User {request.user.username} attempting to add note to claim {claim_id}")
        
        try:
            claim = get_object_or_404(Claim, id=claim_id)
        except Claim.DoesNotExist:
            logger.info(f"Claim {claim_id} not found for adding note")
            return JsonResponse({'error': 'Claim not found'}, status=404)
        
        # Validate and sanitize note text
        note_text = request.POST.get('note_text', '').strip()
        if len(note_text) > 5000:  # Match model constraint
            logger.warning(f"Note text too long for claim {claim_id}: {len(note_text)} characters")
            note_text = note_text[:5000]
        
        note_added = False
        if note_text:
            try:
                with transaction.atomic():
                    Note.objects.create(
                        claim=claim,
                        user=request.user,
                        text=note_text
                    )
                note_added = True
                logger.info(f"Note added to claim {claim_id} by user {request.user.username}")
                
            except ValidationError as e:
                logger.error(f"Validation error adding note to claim {claim_id}: {str(e)}")
                return JsonResponse({'error': 'Invalid note content'}, status=400)
            except DatabaseError as e:
                logger.error(f"Database error adding note to claim {claim_id}: {str(e)}", exc_info=True)
                return JsonResponse({'error': 'Database error occurred'}, status=500)
        else:
            logger.debug(f"Empty note text submitted for claim {claim_id}")
        
        # Get updated notes and annotations with error handling
        try:
            notes = claim.notes.select_related('user').order_by('-created_at')
            flags = claim.flags.select_related('user').order_by('-created_at')
            user_has_flagged = flags.filter(user=request.user).exists()
        except DatabaseError as e:
            logger.error(f"Database error fetching notes/flags after adding note to claim {claim_id}: {str(e)}")
            notes = Note.objects.none()
            flags = Flag.objects.none()
            user_has_flagged = False
        
        context = {
            'claim': claim,
            'notes': notes,
            'flags': flags,
            'user_has_flagged': user_has_flagged,
            'note_added': note_added,
        }
        
        return render(request, 'claims/partials/notes_annotations.html', context)
        
    except Exception as e:
        logger.error(f"Unexpected error in add_note for ID {claim_id}: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)


@login_required
def dashboard(request):
    """Admin dashboard with statistics - Admin only"""
    # Check if user is admin
    if not is_admin_user(request.user):
        messages.error(request, 'Access denied. Dashboard is only available to administrators.')
        return redirect('claims:claims_list')
    # Calculate statistics
    stats = {
        'total_claims': Claim.objects.count(),
        'total_flagged': Flag.objects.values('claim').distinct().count(),
        'total_billed': Claim.objects.aggregate(Sum('billed_amount'))['billed_amount__sum'] or 0,
        'total_paid': Claim.objects.aggregate(Sum('paid_amount'))['paid_amount__sum'] or 0,
    }
    
    # Calculate average underpayment and outstanding amount
    stats['avg_underpayment'] = Claim.objects.aggregate(
        avg_underpayment=Avg(F('billed_amount') - F('paid_amount'))
    )['avg_underpayment'] or 0
    
    # Calculate outstanding amount (total billed - total paid)
    stats['outstanding_amount'] = stats['total_billed'] - stats['total_paid']
    
    # Status breakdown
    status_breakdown = Claim.objects.values('status').annotate(count=Count('id')).order_by('status')
    
    # Recent flags and notes
    recent_flags = Flag.objects.select_related('claim', 'user').order_by('-created_at')[:10]
    recent_notes = Note.objects.select_related('claim', 'user').order_by('-created_at')[:10]
    
    context = {
        'stats': stats,
        'status_breakdown': status_breakdown,
        'recent_flags': recent_flags,
        'recent_notes': recent_notes,
    }
    
    return render(request, 'dashboard/dashboard.html', context)
