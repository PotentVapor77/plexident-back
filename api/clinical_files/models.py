import uuid
from django.db import models
from django.conf import settings
from api.odontogram.models import Paciente, HistorialOdontograma

class ClinicalFile(models.Model):
    class FileType(models.TextChoices):
        XRAY = 'XRAY', 'Radiografía (IMG/DICOM)'
        LAB = 'LAB', 'Laboratorio (PDF)'
        PHOTO = 'PHOTO', 'Fotografía Intraoral'
        MODEL_3D = '3D', 'Modelo 3D (STL/OBJ)'
        OTHER = 'OTHER', 'Otro'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Propiedad y Contexto Clínico
    paciente = models.ForeignKey(Paciente, on_delete=models.PROTECT, related_name='archivos_clinicos')
    # Link opcional a un snapshot específico (inmutabilidad histórica)
    snapshot_version = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="version_id del HistorialOdontograma (agrupa todos los cambios del mismo snapshot)"
    )

    # Metadatos S3 (Off-Database Storage)
    bucket_name = models.CharField(max_length=255)
    s3_key = models.CharField(max_length=1024, help_text="Ruta completa dentro del bucket")
    
    # Metadatos del Archivo
    original_filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100)
    file_size_bytes = models.BigIntegerField()
    category = models.CharField(max_length=20, choices=FileType.choices, default=FileType.OTHER)

    # Auditoría
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'clinical_files'
        indexes = [
            models.Index(fields=['paciente', 'created_at']),
            models.Index(fields=['snapshot_version']),
        ]

    @property
    def is_dicom(self):
        return 'dicom' in self.mime_type or self.original_filename.lower().endswith('.dcm')
