from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
import boto3
import os
import uuid
from datetime import datetime
from .models import FileProcess, ApiCall

def get_s3_client():
    """Helper function to create S3 client using Django settings"""
    return boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME
    )

@login_required
def dashboard_home(request):
    """Dashboard home view showing file processes with statistics"""
    if request.method == 'POST':
        uploaded_file = request.FILES.get('file')
        
        if not uploaded_file:
            messages.error(request, 'Please select a file to upload.')
        else:
            try:
                # Initialize S3 client using settings
                s3_client = get_s3_client()
                
                # Upload to S3 using settings
                bucket_name = settings.AWS_STORAGE_BUCKET_NAME
                s3_key = f"{settings.AWS_BUCKET_FOLDER}/{uploaded_file.name}"
                
                s3_client.upload_fileobj(
                    uploaded_file,
                    bucket_name,
                    s3_key
                )
            except Exception as e:
                messages.error(request, f'Error uploading file: {str(e)}')
                return redirect('core:dashboard_home')
    
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
    api_call = ApiCall.objects.filter(file_process=file_process).first()
    
    context = {
        'file_process': file_process,
        'api_call': api_call,
    }
    
    return render(request, 'core/process_detail.html', context)