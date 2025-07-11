from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from .mixins import UserManagementAccessMixin
from django.contrib.auth.models import User
from django.views.generic import ListView, CreateView, UpdateView, View
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db.models import Q
from .forms import CustomUserCreationForm, CustomUserUpdateForm
import csv
from datetime import datetime
from django.http import HttpResponse

# Create your views here.

def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('core:dashboard_home')
    
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.email}!')
            return redirect('core:dashboard_home')
        else:
            messages.error(request, 'Invalid email or password.')
    
    return render(request, 'account/login.html')

@login_required
def logout_view(request):
    """User logout view"""
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('account:login')

class UserListView(LoginRequiredMixin, UserManagementAccessMixin, ListView):
    """List view for all users with search and filter functionality"""
    model = User
    template_name = 'account/users.html'
    context_object_name = 'users'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = User.objects.all().order_by('-date_joined')
        
        # Search functionality
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(email__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )
        
        # Filter by status
        status_filter = self.request.GET.get('status', '')
        if status_filter == 'active':
            queryset = queryset.filter(is_active=True)
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_users'] = User.objects.count()
        context['active_users'] = User.objects.filter(is_active=True).count()
        context['inactive_users'] = User.objects.filter(is_active=False).count()
        return context

class UserCreateView(LoginRequiredMixin, UserManagementAccessMixin, CreateView):
    """Create new user view"""
    model = User
    form_class = CustomUserCreationForm
    template_name = 'account/user_add.html'
    success_url = reverse_lazy('account:users')
    
    def form_valid(self, form):
        user = form.save()
        messages.success(self.request, f'User "{user.username}" created successfully!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)

class UserUpdateView(LoginRequiredMixin, UserManagementAccessMixin, UpdateView):
    """Update user view"""
    model = User
    template_name = 'account/user_edit.html'
    form_class = CustomUserUpdateForm
    success_url = reverse_lazy('account:users')
    
    def form_valid(self, form):
        user = form.save()
        
        # Handle password reset if provided
        new_password = self.request.POST.get('new_password')
        confirm_password = self.request.POST.get('confirm_password')
        
        if new_password and confirm_password:
            if new_password == confirm_password:
                # Validate password strength
                if len(new_password) >= 8 and any(c.isupper() for c in new_password) and \
                   any(c.islower() for c in new_password) and any(c.isdigit() for c in new_password) and \
                   any(c in '!@#$%^&*(),.?":{}|<>' for c in new_password):
                    
                    user.set_password(new_password)
                    user.save()
                    
                    messages.success(self.request, f'User "{user.username}" updated and password reset successful. New password: {new_password}')
                else:
                    messages.error(self.request, 'Password does not meet strength requirements.')
                    return self.form_invalid(form)
            else:
                messages.error(self.request, 'Passwords do not match.')
                return self.form_invalid(form)
        else:
            messages.success(self.request, f'User "{user.username}" updated successfully!')
        
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)



def get_users_data(request):
    """AJAX endpoint for server-side DataTable processing"""
    try:
        # Check if this is a CSV export request
        if request.GET.get('export') == 'csv':
            return export_users_csv(request)
        
        # Get DataTable parameters
        draw = int(request.GET.get('draw', 1))
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 10))
        search_value = request.GET.get('search[value]', '')
        
        # Get filter parameters
        status_filter = request.GET.get('status', '')
        
        # Build query
        queryset = User.objects.all()
        
        # Apply status filter
        if status_filter == 'active':
            queryset = queryset.filter(is_active=True)
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        # Apply search
        if search_value:
            queryset = queryset.filter(
                Q(email__icontains=search_value) |
                Q(first_name__icontains=search_value) |
                Q(last_name__icontains=search_value)
            )
        
        # Get total count before pagination
        total_records = queryset.count()
        
        # Apply ordering
        queryset = queryset.order_by('-date_joined')
        
        # Apply pagination
        queryset = queryset[start:start + length]
        
        # Prepare data for DataTable
        data = []
        for user in queryset:
            # Get user management access status
            try:
                has_user_access = user.profile.is_user_admin
            except AttributeError:
                has_user_access = False
            
            data.append({
                'id': user.id,
                'email': user.email or '-',
                'full_name': f"{user.first_name} {user.last_name}".strip() or '-',
                'status': 'Active' if user.is_active else 'Inactive',
                'user_access': 'Yes' if has_user_access else 'No',
                'date_joined': user.date_joined.strftime('%b %d, %Y %H:%M'),
                'last_login': user.last_login.strftime('%b %d, %Y %H:%M') if user.last_login else '-',
                'edit_url': reverse_lazy('account:user_edit', kwargs={'pk': user.id})
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

def export_users_csv(request):
    """Export users data to CSV with filters"""
    try:
        # Get filter parameters
        status_filter = request.GET.get('status', '')
        
        # Build query
        queryset = User.objects.all()
        
        # Apply status filter
        if status_filter == 'active':
            queryset = queryset.filter(is_active=True)
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        # Apply ordering
        queryset = queryset.order_by('-date_joined')
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="users_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Username', 'First Name', 'Last Name', 'Email', 'Status', 
            'User Management Access', 'Date Joined', 'Last Login'
        ])
        
        for user in queryset:
            # Get user management access status
            try:
                has_user_access = user.profile.is_user_admin
            except AttributeError:
                has_user_access = False
            
            writer.writerow([
                user.id,
                user.username,
                user.first_name or '',
                user.last_name or '',
                user.email or '',
                'Active' if user.is_active else 'Inactive',
                'Yes' if has_user_access else 'No',
                user.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
                user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else ''
            ])
        
        return response
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def check_email_availability(request):
    """Check if an email is available"""
    email = request.GET.get('email', '')
    if email:
        exists = User.objects.filter(email=email).exists()
        return JsonResponse({'available': not exists})
    return JsonResponse({'available': False})
