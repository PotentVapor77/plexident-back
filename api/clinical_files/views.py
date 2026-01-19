# api/clinical_files/views.py
"""
ViewSet para gestión de archivos clínicos.
Implementa patrón Direct-to-S3 con URLs prefirmadas.
"""
from requests import request
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q
import uuid
import logging

from common.services.storage_service import StorageService

from .models import ClinicalFile
from .serializers import (
    ClinicalFileSerializer,
    ClinicalFileListSerializer,
    FileUploadInitSerializer,
    FileUploadConfirmSerializer
)
from api.odontogram.models import Paciente
from api.users.permissions import UserBasedPermission

logger = logging.getLogger(__name__)


class ClinicalFileViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar archivos clínicos (PDF, JPG, DICOM, STL, etc.)
    
    Endpoints:
    - GET /clinical-files/ - Listar archivos
    - GET /clinical-files/{id}/ - Detalle de archivo
    - POST /clinical-files/init-upload/ - Solicitar URL de subida
    - POST /clinical-files/confirm-upload/ - Confirmar subida
    - DELETE /clinical-files/{id}/ - Eliminar archivo
    - GET /clinical-files/by-patient/{paciente_id}/ - Archivos de un paciente
    """
    
    queryset = ClinicalFile.objects.select_related('paciente', 'uploaded_by', 'snapshot')
    permission_classes = [IsAuthenticated]
    #permission_model_name = 'clinical_files'
    
    def get_serializer_class(self):
        """Usa serializer ligero para listas"""
        if self.action == 'list':
            return ClinicalFileListSerializer
        return ClinicalFileSerializer
    
    def get_queryset(self):
        """Filtrado dinámico por query params"""
        queryset = super().get_queryset()
        
        # Filtro por paciente
        paciente_id = self.request.query_params.get('paciente_id')
        if paciente_id:
            queryset = queryset.filter(paciente_id=paciente_id)
        
        # Filtro por snapshot (historial)
        snapshot_id = self.request.query_params.get('snapshot_id')
        if snapshot_id:
            queryset = queryset.filter(snapshot_id=snapshot_id)
        
        # Filtro por categoría
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # Búsqueda por nombre de archivo
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(original_filename__icontains=search)
        
        return queryset.order_by('-created_at')
    
    @action(detail=False, methods=['post'], url_path='init-upload')
    def init_upload(self, request):
        """
        PASO 1: Solicitar URL prefirmada para subir archivo a S3/MinIO
        
        Body JSON:
        {
            "paciente_id": "uuid",
            "filename": "radiografia.jpg",
            "content_type": "image/jpeg",
            "snapshot_id": "uuid" (opcional),
            "category": "XRAY"
        }
        
        Returns:
        {
            "upload_url": "https://minio:9000/...",
            "s3_key": "pacientes/{uuid}/snapshots/{uuid}/archivos/{uuid}.jpg",
            "file_uuid": "uuid-temporal"
        }
        """
        serializer = FileUploadInitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        paciente_id = serializer.validated_data['paciente_id']
        filename = serializer.validated_data['filename']
        content_type = serializer.validated_data['content_type']
        snapshot_id = serializer.validated_data.get('snapshot_id', 'general')
        
        # Generar UUID único para el archivo
        file_uuid = uuid.uuid4()
        extension = filename.rsplit('.', 1)[-1] if '.' in filename else 'bin'
        
        # Estructura de carpetas: pacientes/{uuid}/snapshots/{uuid}/archivos/{uuid}.ext
        s3_key = f"pacientes/{paciente_id}/snapshots/{snapshot_id}/archivos/{file_uuid}.{extension}"
        
        # Generar URL prefirmada (válida 5 minutos)
        storage = StorageService()
        upload_url = storage.generate_upload_url(s3_key, content_type, expiration=300)
        
        if not upload_url:
            logger.error(f"No se pudo generar URL de subida para {s3_key}")
            return Response(
                {"error": "No se pudo generar URL de subida. Verifique configuración de storage."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        logger.info(f"URL de subida generada para paciente {paciente_id}: {s3_key}")
        
        return Response({
            "upload_url": upload_url,
            "s3_key": s3_key,
            "file_uuid": str(file_uuid)
        }, status=status.HTTP_200_OK)
    @action(detail=False, methods=['post'], url_path='confirm-upload')
    
    def confirm_upload(self, request):
        """
        PASO 2: Confirmar que el archivo se subió exitosamente y crear registro en BD
        
        Body JSON:
        {
            "s3_key": "pacientes/...",
            "paciente_id": "uuid",
            "filename": "radiografia.jpg",
            "content_type": "image/jpeg",
            "size": 1024000,
            "snapshot_id": "uuid" (opcional),
            "category": "XRAY"
        }
        """
        logger.info(f"BODY confirm-upload: {request.data}")  
        serializer = FileUploadConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        s3_key = serializer.validated_data.get('s3_key') 
        if not s3_key:
            # reconstruir o, al menos, loguear mejor el error
            logger.error(f"s3_key faltante en confirm-upload para paciente {serializer.validated_data['paciente_id']}")
            return Response(
                {"error": "Falta s3_key en la confirmación de subida."},
                status=status.HTTP_400_BAD_REQUEST,
    )
        # VALIDACIÓN CRÍTICA: Verificar que el archivo realmente existe en S3
        storage = StorageService()
        if not storage.check_file_exists(s3_key):
            logger.error(f"Archivo no encontrado en storage: {s3_key}")
            return Response(
                {"error": "El archivo no se encuentra en el storage. Intente subir nuevamente."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Crear registro en base de datos
        try:
            clinical_file = ClinicalFile.objects.create(
                paciente_id=serializer.validated_data['paciente_id'],
                snapshot_id=serializer.validated_data.get('snapshot_id'),
                bucket_name=storage._backend.bucket,
                s3_key=s3_key,
                original_filename=serializer.validated_data['filename'],
                mime_type=serializer.validated_data['content_type'],
                file_size_bytes=serializer.validated_data['size'],
                category=serializer.validated_data.get('category', ClinicalFile.FileType.OTHER),
                uploaded_by=request.user
            )
            
            logger.info(f"Archivo clínico creado: {clinical_file.id} - {clinical_file.original_filename}")
            
            return Response(
                ClinicalFileSerializer(clinical_file).data,
                status=status.HTTP_201_CREATED
            )
        
        except Exception as e:
            logger.error(f"Error creando registro de archivo: {e}")
            return Response(
                {"error": "Error al registrar el archivo en la base de datos."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, *args, **kwargs):
        """Eliminar archivo (BD + Storage)"""
        instance = self.get_object()
        s3_key = instance.s3_key
        
        # Eliminar de storage
        storage = StorageService()
        if storage.delete_file(s3_key):
            logger.info(f"Archivo eliminado del storage: {s3_key}")
        else:
            logger.warning(f"No se pudo eliminar del storage: {s3_key}")
        
        # Eliminar de BD
        instance.delete()
        logger.info(f"Registro de archivo eliminado: {instance.id}")
        
        return Response(
            {"message": "Archivo eliminado exitosamente"},
            status=status.HTTP_204_NO_CONTENT
        )
    
    @action(detail=False, methods=['get'], url_path='by-patient/(?P<paciente_id>[^/.]+)')
    def by_patient(self, request, paciente_id=None):
        """
        Listar archivos de un paciente específico
        GET /clinical-files/by-patient/{paciente_id}/
        """
        paciente = get_object_or_404(Paciente, id=paciente_id)
        archivos = self.get_queryset().filter(paciente=paciente)
        
        # Permitir filtro adicional por snapshot
        snapshot_id = request.query_params.get('snapshot_id')
        if snapshot_id:
            archivos = archivos.filter(snapshot_id=snapshot_id)
        
        serializer = self.get_serializer(archivos, many=True)
        
        return Response({
            "paciente": {
                "id": str(paciente.id),
                "nombre_completo": f"{paciente.nombres} {paciente.apellidos}"
            },
            "total_archivos": archivos.count(),
            "archivos": serializer.data
        }, status=status.HTTP_200_OK)
