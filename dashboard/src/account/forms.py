from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import UserProfile

class CustomUserCreationForm(UserCreationForm):
    """Custom form for user creation with additional fields"""
    
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password1', 'password2')
        
    # Add custom admin access field
    is_user_admin = forms.BooleanField(
        required=False,
        label='User Management Access',
        help_text='If checked, this user will have access to the user management console.',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add Bootstrap classes to form fields
        for field_name, field in self.fields.items():
            if field.widget.input_type in ['text', 'email', 'password']:
                field.widget.attrs.update({
                    'class': 'form-control',
                    'placeholder': field.label
                })
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({
                    'class': 'form-check-input'
                })
        
        # Customize help text for password fields
        self.fields['password1'].help_text = """
        """
        
        # Make email field required
        self.fields['email'].required = True
        
    def clean_email(self):
        """Validate email uniqueness and set as username"""
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with this email address already exists.')
        return email
    
    def save(self, commit=True):
        """Save user and create/update profile"""
        user = super().save(commit=False)
        # Set email as username
        user.username = self.cleaned_data.get('email')
        user.is_staff = False
        user.is_superuser = False
        user.is_active = True
        
        if commit:
            user.save()
            # Create or update profile
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.is_user_admin = self.cleaned_data.get('is_user_admin', False)
            profile.save()
        
        return user

class CustomUserUpdateForm(forms.ModelForm):
    """Custom form for user updates"""
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'is_active')
        
    # Add custom admin access field
    is_user_admin = forms.BooleanField(
        required=False,
        label='User Management Access',
        help_text='If checked, this user will have access to the user management console.',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add Bootstrap classes to form fields
        for field_name, field in self.fields.items():
            if field.widget.input_type in ['text', 'email']:
                field.widget.attrs.update({
                    'class': 'form-control',
                    'placeholder': field.label
                })
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({
                    'class': 'form-check-input'
                })
        
    def clean_email(self):
        """Validate email uniqueness and update username (excluding current user)"""
        email = self.cleaned_data.get('email')
        if email:
            # Check if email exists for other users
            users_with_email = User.objects.filter(email=email)
            if self.instance.pk:
                users_with_email = users_with_email.exclude(pk=self.instance.pk)
            
            if users_with_email.exists():
                raise forms.ValidationError('A user with this email address already exists.')
        return email
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set initial value for is_user_admin from profile
        if self.instance and self.instance.pk:
            try:
                self.fields['is_user_admin'].initial = self.instance.profile.is_user_admin
            except UserProfile.DoesNotExist:
                pass
    
    def save(self, commit=True):
        """Save user and update profile"""
        user = super().save(commit=False)
        # Update username to match email
        user.username = self.cleaned_data.get('email')
        
        if commit:
            user.save()
            # Update profile
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.is_user_admin = self.cleaned_data.get('is_user_admin', False)
            profile.save()
        
        return user 