from django.shortcuts import render, get_object_or_404
from django.db.models import Count, Q
from django.contrib.auth.decorators import login_required
from .models import FileProcess, ApiCall

@login_required
def dashboard_home(request):
    """Dashboard home view showing file processes with statistics"""
    
    # Get statistics for cards
    total_processes = FileProcess.objects.count()
    pending_processes = FileProcess.objects.filter(status='Pending').count()
    processing_processes = FileProcess.objects.filter(status='Processing').count()
    completed_processes = FileProcess.objects.filter(status='Processed').count()
    failed_processes = FileProcess.objects.filter(status='Failed').count()
    
    # Get all file processes for the table
    file_processes = FileProcess.objects.all().order_by('-created_at')
    
    context = {
        'total_processes': total_processes,
        'pending_processes': pending_processes,
        'processing_processes': processing_processes,
        'completed_processes': completed_processes,
        'failed_processes': failed_processes,
        'file_processes': file_processes,
    }
    
    return render(request, 'core/dashboard.html', context)

@login_required
def process_detail(request, process_id):
    """Detail view for a specific file process showing all API calls"""
    
    # Get the file process
    file_process = get_object_or_404(FileProcess, unique_id=process_id)
    
    # Get all API calls for this process
    api_calls = ApiCall.objects.filter(file_process=file_process).order_by('row_number')
    
    # Get statistics for this process
    total_api_calls = api_calls.count()
    successful_calls = api_calls.filter(api_status__gte=200, api_status__lt=300).count()
    failed_calls = api_calls.filter(Q(api_status__lt=200) | Q(api_status__gte=300)).count()
    error_calls = api_calls.filter(error_message__isnull=False).count()
    
    context = {
        'file_process': file_process,
        'api_calls': api_calls,
        'total_api_calls': total_api_calls,
        'successful_calls': successful_calls,
        'failed_calls': failed_calls,
        'error_calls': error_calls,
    }
    
    return render(request, 'core/process_detail.html', context)
