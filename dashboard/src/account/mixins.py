from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect
from django.contrib import messages

class UserManagementAccessMixin(AccessMixin):
    """Mixin to check if user has access to user management"""
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # Check if user has user management access
        try:
            if not request.user.is_superuser and not request.user.profile.is_user_admin:
                messages.error(request, 'You do not have permission to access user management.')
                return redirect('core:dashboard_home')
        except AttributeError:
            # If user doesn't have a profile, they don't have access
            messages.error(request, 'You do not have permission to access user management.')
            return redirect('core:dashboard_home')
        
        return super().dispatch(request, *args, **kwargs) 