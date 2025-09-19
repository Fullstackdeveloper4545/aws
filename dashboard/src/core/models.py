from django.db import models
import uuid

class FileProcess(models.Model):
    """Model for tracking file processing status"""
    
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Downloaded', 'Downloaded'),
        ('Uploaded', 'Uploaded'),
        ('Queued', 'Queued'),
        ('Processing', 'Processing'),
        ('Processed', 'Processed'),
        ('Failed', 'Failed'),
    ]
    
    unique_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site_id = models.CharField(max_length=255, null=True, blank=True)
    filename = models.CharField(max_length=255)
    location = models.CharField(max_length=500, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'file_processes'
        verbose_name = 'File Process'
        verbose_name_plural = 'File Processes'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.filename} - {self.status} ({self.unique_id})"

class ApiCall(models.Model):
    """Model for tracking API calls made during file transformation"""

    json_payload = models.JSONField()
    api_status = models.IntegerField()
    api_response = models.TextField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Foreign key relationship to FileProcess
    file_process = models.ForeignKey(
        FileProcess, 
        on_delete=models.CASCADE, 
        related_name='api_calls',
        to_field='unique_id',
        db_column='unique_id'
    )
    
    class Meta:
        db_table = 'api_calls'
        verbose_name = 'API Call'
        verbose_name_plural = 'API Calls'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"API Call for {self.file_process} - Status: {self.api_status}"
    
    @property
    def is_successful(self):
        """Check if the API call was successful"""
        return 200 <= self.api_status < 300
    
    @property
    def has_error(self):
        """Check if the API call had an error"""
        return self.error_message is not None or self.api_status == 0

class EmailConfig(models.Model):
    """Model for storing email configuration"""
    
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'email_configs'
        verbose_name = 'Email Configuration'
        verbose_name_plural = 'Email Configurations'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.email}"

class Credentials(models.Model):
    """Model for storing credentials that can be connected with multiple site IDs"""
    
    CREDENTIAL_TYPE_CHOICES = [
        ('api', 'API'),
        ('api-certificate', 'API-CERTIFICATE')
    ]
    
    unique_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, help_text="A descriptive name for these credentials")
    credential_type = models.CharField(max_length=20, choices=CREDENTIAL_TYPE_CHOICES, default='other')
    username = models.CharField(max_length=255, null=True, blank=True)
    password = models.CharField(max_length=255, null=True, blank=True)
    api_key = models.CharField(max_length=500, null=True, blank=True)
    secret_key = models.CharField(max_length=500, null=True, blank=True)
    certificate = models.FileField(upload_to='certificates/', null=True, blank=True, help_text="Upload a certificate file if required")
    additional_config = models.JSONField(null=True, blank=True, help_text="Additional configuration as JSON")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'credentials'
        verbose_name = 'Credential'
        verbose_name_plural = 'Credentials'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.credential_type})"
    
    @property
    def site_ids(self):
        """Get all site IDs associated with these credentials"""
        return [site_cred.site_id for site_cred in self.site_credentials.all()]

class SiteCredential(models.Model):
    """Model for connecting credentials with site IDs (many-to-many relationship)"""
    
    credentials = models.ForeignKey(
        Credentials,
        on_delete=models.CASCADE,
        related_name='site_credentials'
    )
    site_id = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'site_credentials'
        verbose_name = 'Site Credential'
        verbose_name_plural = 'Site Credentials'
        unique_together = ['credentials', 'site_id']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.credentials.name} - Site: {self.site_id}"

class BNSFWaybill(models.Model):
    """Model for storing BNSF waybill data"""
    
    unique_id = models.UUIDField(default=uuid.uuid4, editable=False)
    equipment_initial = models.CharField(max_length=10)
    equipment_number = models.CharField(max_length=20)
    waybill_data = models.JSONField()
    processed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'bnsf_waybills'
        verbose_name = 'BNSF Waybill'
        verbose_name_plural = 'BNSF Waybills'
        ordering = ['-processed_at']
    
    def __str__(self):
        return f"{self.equipment_initial}{self.equipment_number} ({self.processed_at})"

class BNSFCertificate(models.Model):
    """Model for storing BNSF API certificate information"""
    
    name = models.CharField(max_length=100)
    client_pfx = models.FileField(upload_to='certificates/')
    server_cer = models.FileField(upload_to='certificates/')
    pfx_password = models.CharField(max_length=100)
    # Backward-compatible default. Use specific URLs below when provided.
    api_url = models.URLField(default="https://api-trial.bnsf.com:6443/v1/cars")
    cars_api_url = models.URLField(null=True, blank=True)
    waybill_api_url = models.URLField(null=True, blank=True)
    skip_verify = models.BooleanField(default=False)
    site_id = models.CharField(max_length=255, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'bnsf_certificates'
        verbose_name = 'BNSF Certificate'
        verbose_name_plural = 'BNSF Certificates'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.created_at})"