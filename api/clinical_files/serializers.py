# api/clinical_files/serializers.py
"""
Serializers para el módulo de archivos clínicos.
Maneja validación y transformación de datos.
"""
from rest_framework import serializers

from common.services.storage_service import StorageService
from .models import ClinicalFile
from api.odontogram.models import Paciente
import uuid


class FileUploadInitSerializer(serializers.Serializer):
    """Validador para iniciar la carga de archivo"""
    paciente_id = serializers.UUIDField(required=True)
    filename = serializers.CharField(max_length=255, required=True)
    content_type = serializers.CharField(max_length=100, required=True)
    snapshot_id = serializers.UUIDField(required=False, allow_null=True)
    category = serializers.ChoiceField(
        choices=ClinicalFile.FileType.choices,
        default=ClinicalFile.FileType.OTHER
    )
    
    def validate_paciente_id(self, value):
        """Verifica que el paciente exista"""
        if not Paciente.objects.filter(id=value).exists():
            raise serializers.ValidationError("El paciente no existe")
        return value
    
    def validate_filename(self, value):
        """Validación básica del nombre de archivo"""
        if '..' in value or '/' in value or '\\' in value:
            raise serializers.ValidationError("Nombre de archivo inválido")
        return value


class FileUploadConfirmSerializer(serializers.Serializer):
    """Validador para confirmar la subida de archivo"""
    s3_key = serializers.CharField(max_length=1024, required=False, allow_blank=True)
    paciente_id = serializers.UUIDField(required=True)
    filename = serializers.CharField(max_length=255, required=True)
    content_type = serializers.CharField(max_length=100, required=True)
    size = serializers.IntegerField(min_value=1, required=True)
    snapshot_id = serializers.UUIDField(required=False, allow_null=True)
    category = serializers.ChoiceField(
        choices=ClinicalFile.FileType.choices,
        default=ClinicalFile.FileType.OTHER
    )


class ClinicalFileSerializer(serializers.ModelSerializer):
    """Serializer principal para archivos clínicos"""
    uploaded_by_name = serializers.SerializerMethodField()
    paciente_nombre = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    
    class Meta:
        model = ClinicalFile
        fields = [
            'id', 'paciente', 'paciente_nombre', 'snapshot_version',
            'original_filename', 'mime_type', 'file_size_bytes',
            'category', 'uploaded_by', 'uploaded_by_name',
            'created_at', 'file_url', 'download_url', 'is_dicom'
        ]
        read_only_fields = [
            'id', 'bucket_name', 's3_key', 'uploaded_by', 'created_at'
        ]
    
    def get_uploaded_by_name(self, obj):
        """Nombre completo del usuario que subió el archivo"""
        if hasattr(obj.uploaded_by, 'get_full_name'):
            return obj.uploaded_by.get_full_name()
        return str(obj.uploaded_by)
    
    def get_paciente_nombre(self, obj):
        """Nombre completo del paciente"""
        return f"{obj.paciente.nombres} {obj.paciente.apellidos}"
    
    def get_file_url(self, obj):
        """URL para visualizar (expira en 1 hora)"""
        storage = StorageService()
        return storage.generate_view_url(obj.s3_key, expiration=3600)
    
    def get_download_url(self, obj):
        """URL para descargar con nombre original"""
        storage = StorageService()
        return storage.generate_view_url(
            obj.s3_key, 
            expiration=3600, 
            download_name=obj.original_filename
        )


class ClinicalFileListSerializer(serializers.ModelSerializer):
    """Serializer ligero para listados (sin URLs)"""
    uploaded_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = ClinicalFile
        fields = [
            'id', 'original_filename', 'mime_type', 
            'file_size_bytes', 'category', 'created_at',
            'uploaded_by_name', 'is_dicom'
        ]
    
    def get_uploaded_by_name(self, obj):
        if hasattr(obj.uploaded_by, 'get_full_name'):
            return obj.uploaded_by.get_full_name()
        return str(obj.uploaded_by)
