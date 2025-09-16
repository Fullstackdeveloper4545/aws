from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.urls import reverse
from datetime import datetime
import csv
from .models import FileProcess, ApiCall, EmailConfig, Credentials, SiteCredential, BNSFWaybill, BNSFCertificate
from account.mixins import UserManagementAccessMixin
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy

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
    api_call = ApiCall.objects.filter(file_process=file_process).first()
    
    context = {
        'file_process': file_process,
        'api_call': api_call,
    }
    
    return render(request, 'core/process_detail.html', context)

@login_required
def get_processes_data(request):
    """AJAX endpoint for server-side DataTable processing"""
    try:
        # Check if this is a CSV export request
        if request.GET.get('export') == 'csv':
            return export_processes_csv(request)
        
        # Get DataTable parameters
        draw = int(request.GET.get('draw', 1))
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 10))
        search_value = request.GET.get('search[value]', '')
        
        # Get filter parameters
        site_id = request.GET.get('site_id', '')
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        status_filter = request.GET.get('status', '')
        
        # Build query
        queryset = FileProcess.objects.all()
        
        # Apply filters
        if site_id:
            queryset = queryset.filter(site_id__icontains=site_id)
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                queryset = queryset.filter(created_at__date__gte=date_from_obj.date())
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
                queryset = queryset.filter(created_at__date__lte=date_to_obj.date())
            except ValueError:
                pass
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Apply search
        if search_value:
            queryset = queryset.filter(
                Q(filename__icontains=search_value) |
                Q(site_id__icontains=search_value) |
                Q(location__icontains=search_value) |
                Q(status__icontains=search_value)
            )
        
        # Get total count before pagination
        total_records = queryset.count()
        
        # Apply ordering
        queryset = queryset.order_by('-created_at')
        
        # Apply pagination
        queryset = queryset[start:start + length]
        
        # Prepare data for DataTable
        data = []
        for process in queryset:
            data.append({
                'id': str(process.unique_id)[:8],
                'filename': process.filename,
                'status': process.status,
                'location': process.location or '-',
                'created_at': process.created_at.strftime('%b %d, %Y %H:%M'),
                'updated_at': process.updated_at.strftime('%b %d, %Y %H:%M'),
                'site_id': process.site_id or '-',
                'detail_url': reverse('core:process_detail', kwargs={'process_id': process.unique_id})
            })
        
        return JsonResponse({
            'draw': draw,
            'recordsTotal': total_records,
            'recordsFiltered': total_records,
            'data': data
        })
        
    except Exception as e:
        return JsonResponse({
            'draw': int(request.GET.get('draw', 1)),
            'recordsTotal': 0,
            'recordsFiltered': 0,
            'data': [],
            'error': str(e)
        }, status=500)

def export_processes_csv(request):
    """Export processes data to CSV with filters"""
    try:
        # Get filter parameters
        site_id = request.GET.get('site_id', '')
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')
        status_filter = request.GET.get('status', '')
        
        # Build query
        queryset = FileProcess.objects.all()
        
        # Apply filters
        if site_id:
            queryset = queryset.filter(site_id__icontains=site_id)
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                queryset = queryset.filter(created_at__date__gte=date_from_obj.date())
            except ValueError:
                pass
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
                queryset = queryset.filter(created_at__date__lte=date_to_obj.date())
            except ValueError:
                pass
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Apply ordering
        queryset = queryset.order_by('-created_at')
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="file_processes_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Site ID', 'Filename', 'Status', 'Location', 
            'Created At', 'Updated At', 'Error Message'
        ])
        
        for process in queryset:
            writer.writerow([
                str(process.unique_id)[:8],
                process.site_id or '',
                process.filename,
                process.status,
                process.location or '',
                process.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                process.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                process.error_message or ''
            ])
        
        return response
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

class EmailConfigListView(LoginRequiredMixin, UserManagementAccessMixin, ListView):
    """List all email configurations"""
    model = EmailConfig
    template_name = 'core/email_config_list.html'
    context_object_name = 'email_configs'
    ordering = ['-created_at']

class EmailConfigCreateView(LoginRequiredMixin, UserManagementAccessMixin, CreateView):
    """Add a new email configuration"""
    model = EmailConfig
    template_name = 'core/email_config_form.html'
    fields = ['email']
    success_url = reverse_lazy('core:email_config_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Add'
        return context
    
    def form_valid(self, form):
        # Check if email already exists
        if EmailConfig.objects.filter(email=form.cleaned_data['email']).exists():
            messages.error(self.request, 'This email address is already configured.')
            return self.form_invalid(form)
        
        messages.success(self.request, 'Email configuration added successfully.')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

class EmailConfigUpdateView(LoginRequiredMixin, UserManagementAccessMixin, UpdateView):
    """Edit an existing email configuration"""
    model = EmailConfig
    template_name = 'core/email_config_form.html'
    fields = ['email']
    success_url = reverse_lazy('core:email_config_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Edit'
        return context
    
    def form_valid(self, form):
        # Check if email already exists (excluding current record)
        if EmailConfig.objects.filter(email=form.cleaned_data['email']).exclude(id=self.object.id).exists():
            messages.error(self.request, 'This email address is already configured.')
            return self.form_invalid(form)
        
        messages.success(self.request, 'Email configuration updated successfully.')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

class EmailConfigDeleteView(LoginRequiredMixin, UserManagementAccessMixin, DeleteView):
    """Delete an email configuration"""
    model = EmailConfig
    template_name = 'core/email_config_confirm_delete.html'
    success_url = reverse_lazy('core:email_config_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Email configuration deleted successfully.')
        return super().delete(request, *args, **kwargs)

# Credentials Views
class CredentialsListView(LoginRequiredMixin, UserManagementAccessMixin, ListView):
    """List all credentials"""
    model = Credentials
    template_name = 'core/credentials_list.html'
    context_object_name = 'credentials'
    ordering = ['-created_at']

class CredentialsCreateView(LoginRequiredMixin, UserManagementAccessMixin, CreateView):
    """Add a new credential"""
    model = Credentials
    template_name = 'core/credentials_form.html'
    fields = [
        'name', 'credential_type', 
        # 'username', 'password', 
        'api_key', 'secret_key',
        'additional_config', 'is_active'
    ]
    success_url = reverse_lazy('core:credentials_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Add'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Credential added successfully.')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

class CredentialsUpdateView(LoginRequiredMixin, UserManagementAccessMixin, UpdateView):
    """Edit an existing credential"""
    model = Credentials
    template_name = 'core/credentials_form.html'
    fields = [
        'name', 'credential_type', 
        # 'username', 'password', 
        'api_key', 'secret_key',
        'additional_config', 'is_active'
    ]
    success_url = reverse_lazy('core:credentials_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Edit'
        return context
    
    def form_valid(self, form):
        messages.success(self.request, 'Credential updated successfully.')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

class CredentialsDeleteView(LoginRequiredMixin, UserManagementAccessMixin, DeleteView):
    """Delete a credential"""
    model = Credentials
    template_name = 'core/credentials_confirm_delete.html'
    success_url = reverse_lazy('core:credentials_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Credential deleted successfully.')
        return super().delete(request, *args, **kwargs)

class CredentialsDetailView(LoginRequiredMixin, UserManagementAccessMixin, UpdateView):
    """Detail view for credentials showing associated site IDs"""
    model = Credentials
    template_name = 'core/credentials_detail.html'
    fields = []
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['site_credentials'] = self.object.site_credentials.all().order_by('site_id')
        return context

# Site Credential Views
class SiteCredentialListView(LoginRequiredMixin, UserManagementAccessMixin, ListView):
    """List all site credential associations"""
    model = SiteCredential
    template_name = 'core/site_credential_list.html'
    context_object_name = 'site_credentials'
    ordering = ['-created_at']

class SiteCredentialCreateView(LoginRequiredMixin, UserManagementAccessMixin, CreateView):
    """Add a new site credential association"""
    model = SiteCredential
    template_name = 'core/site_credential_form.html'
    fields = ['credentials', 'site_id', 'is_active']
    success_url = reverse_lazy('core:site_credential_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Add'
        context['credentials_list'] = Credentials.objects.filter(is_active=True).order_by('name')
        return context
    
    def form_valid(self, form):
        # Check if this association already exists
        if SiteCredential.objects.filter(
            credentials=form.cleaned_data['credentials'],
            site_id=form.cleaned_data['site_id']
        ).exists():
            messages.error(self.request, 'This credential is already associated with this site ID.')
            return self.form_invalid(form)
        
        messages.success(self.request, 'Site credential association added successfully.')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

class SiteCredentialUpdateView(LoginRequiredMixin, UserManagementAccessMixin, UpdateView):
    """Edit an existing site credential association"""
    model = SiteCredential
    template_name = 'core/site_credential_form.html'
    fields = ['credentials', 'site_id', 'is_active']
    success_url = reverse_lazy('core:site_credential_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Edit'
        context['credentials_list'] = Credentials.objects.filter(is_active=True).order_by('name')
        return context
    
    def form_valid(self, form):
        # Check if this association already exists (excluding current record)
        if SiteCredential.objects.filter(
            credentials=form.cleaned_data['credentials'],
            site_id=form.cleaned_data['site_id']
        ).exclude(id=self.object.id).exists():
            messages.error(self.request, 'This credential is already associated with this site ID.')
            return self.form_invalid(form)
        
        messages.success(self.request, 'Site credential association updated successfully.')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

class SiteCredentialDeleteView(LoginRequiredMixin, UserManagementAccessMixin, DeleteView):
    """Delete a site credential association"""
    model = SiteCredential
    template_name = 'core/site_credential_confirm_delete.html'
    success_url = reverse_lazy('core:site_credential_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Site credential association deleted successfully.')
        return super().delete(request, *args, **kwargs)

# AJAX Views for Credentials
@login_required
def get_credentials_data(request):
    """AJAX endpoint for server-side DataTable processing for credentials"""
    try:
        # Get DataTable parameters
        draw = int(request.GET.get('draw', 1))
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 10))
        search_value = request.GET.get('search[value]', '')
        
        # Get filter parameters
        credential_type = request.GET.get('credential_type', '')
        is_active = request.GET.get('is_active', '')
        
        # Build query
        queryset = Credentials.objects.all()
        
        # Apply filters
        if credential_type:
            queryset = queryset.filter(credential_type=credential_type)
        
        if is_active != '':
            queryset = queryset.filter(is_active=is_active == 'true')
        
        # Apply search
        if search_value:
            queryset = queryset.filter(
                Q(name__icontains=search_value) |
                Q(username__icontains=search_value) |
                Q(host__icontains=search_value) |
                Q(credential_type__icontains=search_value)
            )
        
        # Get total count before pagination
        total_records = queryset.count()
        
        # Apply ordering
        queryset = queryset.order_by('-created_at')
        
        # Apply pagination
        queryset = queryset[start:start + length]
        
        # Prepare data for DataTable
        data = []
        for credential in queryset:
            data.append({
                'id': str(credential.unique_id)[:8],
                'name': credential.name,
                'credential_type': credential.get_credential_type_display(),
                'username': credential.username or '-',
                'site_count': credential.site_credentials.count(),
                'is_active': 'Yes' if credential.is_active else 'No',
                'created_at': credential.created_at.strftime('%b %d, %Y %H:%M'),
                'detail_url': reverse('core:credentials_detail', kwargs={'pk': credential.unique_id}),
                'edit_url': reverse('core:credentials_update', kwargs={'pk': credential.unique_id}),
                'delete_url': reverse('core:credentials_delete', kwargs={'pk': credential.unique_id})
            })
        
        return JsonResponse({
            'draw': draw,
            'recordsTotal': total_records,
            'recordsFiltered': total_records,
            'data': data
        })
        
    except Exception as e:
        return JsonResponse({
            'draw': int(request.GET.get('draw', 1)),
            'recordsTotal': 0,
            'recordsFiltered': 0,
            'data': [],
            'error': str(e)
        }, status=500)

@login_required
def get_site_credentials_data(request):
    """AJAX endpoint for server-side DataTable processing for site credentials"""
    try:
        # Get DataTable parameters
        draw = int(request.GET.get('draw', 1))
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 10))
        search_value = request.GET.get('search[value]', '')
        
        # Get filter parameters
        site_id = request.GET.get('site_id', '')
        credential_name = request.GET.get('credential_name', '')
        is_active = request.GET.get('is_active', '')
        
        # Build query
        queryset = SiteCredential.objects.select_related('credentials').all()
        
        # Apply filters
        if site_id:
            queryset = queryset.filter(site_id__icontains=site_id)
        
        if credential_name:
            queryset = queryset.filter(credentials__name__icontains=credential_name)
        
        if is_active != '':
            queryset = queryset.filter(is_active=is_active == 'true')
        
        # Apply search
        if search_value:
            queryset = queryset.filter(
                Q(site_id__icontains=search_value) |
                Q(credentials__name__icontains=search_value) |
                Q(credentials__credential_type__icontains=search_value)
            )
        
        # Get total count before pagination
        total_records = queryset.count()
        
        # Apply ordering
        queryset = queryset.order_by('-created_at')
        
        # Apply pagination
        queryset = queryset[start:start + length]
        
        # Prepare data for DataTable
        data = []
        for site_cred in queryset:
            data.append({
                'id': site_cred.id,
                'site_id': site_cred.site_id,
                'credential_name': site_cred.credentials.name,
                'credential_type': site_cred.credentials.get_credential_type_display(),
                'is_active': 'Yes' if site_cred.is_active else 'No',
                'created_at': site_cred.created_at.strftime('%b %d, %Y %H:%M'),
                'edit_url': reverse('core:site_credential_update', kwargs={'pk': site_cred.id}),
                'delete_url': reverse('core:site_credential_delete', kwargs={'pk': site_cred.id})
            })
        
        return JsonResponse({
            'draw': draw,
            'recordsTotal': total_records,
            'recordsFiltered': total_records,
            'data': data
        })
        
    except Exception as e:
        return JsonResponse({
            'draw': int(request.GET.get('draw', 1)),
            'recordsTotal': 0,
            'recordsFiltered': 0,
            'data': [],
            'error': str(e)
        }, status=500)