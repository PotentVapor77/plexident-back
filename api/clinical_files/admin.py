# api/clinical_files/admin.py
from django.contrib import admin
from .models import ClinicalFile


@admin.register(ClinicalFile)
class ClinicalFileAdmin(admin.ModelAdmin):
    list_display = ['original_filename', 'paciente', 'category', 'file_size_mb', 'uploaded_by', 'created_at']
    list_filter = ['category', 'created_at', 'mime_type']
    search_fields = ['original_filename', 'paciente__nombres', 'paciente__apellidos']
    readonly_fields = ['id', 'bucket_name', 's3_key', 'created_at', 'is_dicom']
    
    def file_size_mb(self, obj):
        return f"{obj.file_size_bytes / 1024 / 1024:.2f} MB"
    file_size_mb.short_description = 'Tamaño'
