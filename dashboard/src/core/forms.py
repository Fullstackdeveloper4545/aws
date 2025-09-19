from django import forms
from .models import Credentials, SiteCredential, BNSFCertificate

class CredentialsForm(forms.ModelForm):
    """Form for managing credentials"""
    
    class Meta:
        model = Credentials
        fields = [
            'name', 'credential_type', 
            'api_key', 'secret_key',
            'additional_config', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'credential_type': forms.Select(attrs={'class': 'form-control'}),
            'api_key': forms.TextInput(attrs={'class': 'form-control'}),
            'secret_key': forms.TextInput(attrs={'class': 'form-control'}),
            'additional_config': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
        labels = {
            'name': 'Credential Name',
            'credential_type': 'Credential Type',
            'api_key': 'API Key',
            'secret_key': 'Secret Key',
            'additional_config': 'Additional Configuration (JSON)',
            'is_active': 'Active'
        }

class SiteCredentialForm(forms.ModelForm):
    """Form for managing site credential associations"""
    
    class Meta:
        model = SiteCredential
        fields = ['credentials', 'site_id', 'is_active']
        widgets = {
            'credentials': forms.Select(attrs={'class': 'form-control'}),
            'site_id': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
        labels = {
            'credentials': 'Credential',
            'site_id': 'Site ID',
            'is_active': 'Active'
        }

class BNSFCertificateForm(forms.ModelForm):
    """Form for managing BNSF certificates"""
    
    pfx_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='Password for the PFX certificate'
    )
    
    class Meta:
        model = BNSFCertificate
        fields = ['name', 'client_pfx', 'server_cer', 'pfx_password', 'api_url', 'skip_verify', 'site_id', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'client_pfx': forms.FileInput(attrs={'class': 'form-control'}),
            'server_cer': forms.FileInput(attrs={'class': 'form-control'}),
            'api_url': forms.URLInput(attrs={'class': 'form-control'}),
            'skip_verify': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'site_id': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
        labels = {
            'name': 'Certificate Name',
            'client_pfx': 'Client PFX Certificate',
            'server_cer': 'Server CER Certificate',
            'pfx_password': 'PFX Password',
            'api_url': 'BNSF API URL',
            'skip_verify': 'Skip SSL Verification (Development Only)',
            'site_id': 'Site ID (Optional)',
            'is_active': 'Active'
        }

    def save(self, commit=True):
        """Force new certificates to be active by default regardless of checkbox state."""
        instance = super().save(commit=False)
        instance.is_active = True
        if commit:
            instance.save()
        return instance
