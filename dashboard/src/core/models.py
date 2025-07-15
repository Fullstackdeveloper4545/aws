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