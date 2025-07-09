from django.contrib import admin
from .models import FileProcess, ApiCall

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
