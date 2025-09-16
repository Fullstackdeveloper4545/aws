from django.contrib import admin
from .models import FileProcess, ApiCall, EmailConfig, Credentials, SiteCredential, BNSFWaybill, BNSFCertificate

@admin.register(FileProcess)
class FileProcessAdmin(admin.ModelAdmin):
    list_display = ('filename', 'status', 'created_at', 'updated_at', 'unique_id')
    list_filter = ('status', 'created_at')
    search_fields = ('filename', 'unique_id')
    readonly_fields = ('unique_id', 'created_at', 'updated_at')
    ordering = ('-created_at',)

@admin.register(ApiCall)
class ApiCallAdmin(admin.ModelAdmin):
    list_display = ('file_process', 'api_status', 'created_at', 'is_successful')
    list_filter = ('api_status', 'created_at', 'file_process__status')
    search_fields = ('file_process__filename', 'error_message')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)
    
    def is_successful(self, obj):
        return obj.is_successful
    is_successful.boolean = True
    is_successful.short_description = 'Successful'

@admin.register(EmailConfig)
class EmailConfigAdmin(admin.ModelAdmin):
    list_display = ('email', 'created_at', 'updated_at')
    list_filter = ('created_at',)
    search_fields = ('email',)
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Email Information', {
            'fields': ('email',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Credentials)
class CredentialsAdmin(admin.ModelAdmin):
    list_display = ['name', 'credential_type', 'is_active', 'created_at']
    list_filter = ['credential_type', 'is_active', 'created_at']
    search_fields = ['name', 'username', 'host']
    readonly_fields = ['unique_id', 'created_at', 'updated_at']
    ordering = ['-created_at']

@admin.register(SiteCredential)
class SiteCredentialAdmin(admin.ModelAdmin):
    list_display = ['credentials', 'site_id', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['credentials__name', 'site_id']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

@admin.register(BNSFWaybill)
class BNSFWaybillAdmin(admin.ModelAdmin):
    list_display = ['equipment_initial', 'equipment_number', 'processed_at']
    list_filter = ['processed_at', 'equipment_initial']
    search_fields = ['equipment_initial', 'equipment_number']
    readonly_fields = ['unique_id', 'processed_at']
    ordering = ['-processed_at']

@admin.register(BNSFCertificate)
class BNSFCertificateAdmin(admin.ModelAdmin):
    list_display = ['name', 'api_url', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'api_url', 'site_id']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
