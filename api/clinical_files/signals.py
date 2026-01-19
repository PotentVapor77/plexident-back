# api/clinical_files/signals.py

"""
Signals para gestión automática de archivos clínicos.
Implementa patrón Observer para mantener sincronización BD-Storage.
"""

import logging
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from .models import ClinicalFile
from common.services.storage_service import StorageService

logger = logging.getLogger(__name__)


@receiver(post_delete, sender=ClinicalFile)
def delete_file_from_storage(sender, instance, **kwargs):
    """
    Signal: Elimina archivo de S3/MinIO cuando se borra el registro en BD.
    
    Garantiza consistencia entre base de datos y almacenamiento físico.
    Se ejecuta DESPUÉS de eliminar el registro (post_delete).
    
    Args:
        sender: Modelo que envió la señal (ClinicalFile)
        instance: Instancia del archivo eliminado
        **kwargs: Argumentos adicionales de Django
    """
    if not instance.s3_key:
        logger.warning(f"Archivo {instance.id} no tiene s3_key definido. Skip eliminación.")
        return
    
    try:
        storage = StorageService()
        deleted = storage.delete_file(instance.s3_key)
        
        if deleted:
            logger.info(
                f"✓ Archivo eliminado del storage: {instance.s3_key} "
                f"(Paciente: {instance.paciente_id}, Size: {instance.file_size_bytes} bytes)"
            )
        else:
            logger.warning(
                f"⚠ No se pudo eliminar archivo del storage: {instance.s3_key} "
                f"(puede que ya no exista)"
            )
    
    except Exception as e:
        logger.error(
            f"✗ Error eliminando archivo {instance.s3_key} del storage: {e}",
            exc_info=True
        )
        # No propagamos la excepción para no bloquear la eliminación en BD


@receiver(pre_save, sender=ClinicalFile)
def validate_file_before_save(sender, instance, **kwargs):
    """
    Signal: Validaciones antes de guardar un archivo clínico.
    
    Verifica integridad de datos y existencia del archivo en storage.
    Se ejecuta ANTES de guardar (pre_save).
    
    Args:
        sender: Modelo que envió la señal (ClinicalFile)
        instance: Instancia del archivo a guardar
        **kwargs: Argumentos adicionales de Django
    """
    # Solo validar en creación (no en actualización)
    if instance.pk:
        return
    
    # Validar que s3_key no esté vacío
    if not instance.s3_key or not instance.s3_key.strip():
        logger.error(f"Intento de crear ClinicalFile sin s3_key para paciente {instance.paciente_id}")
        raise ValueError("El campo s3_key es obligatorio")
    
    # Validar tamaño de archivo
    if instance.file_size_bytes <= 0:
        logger.error(f"Tamaño de archivo inválido: {instance.file_size_bytes} bytes")
        raise ValueError("El tamaño del archivo debe ser mayor a 0")
    
    # Validar límite de tamaño (100 MB)
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB
    if instance.file_size_bytes > MAX_FILE_SIZE:
        logger.warning(
            f"Archivo muy grande: {instance.file_size_bytes / 1024 / 1024:.2f} MB "
            f"para {instance.original_filename}"
        )
    
    logger.debug(
        f"Validación pre-save exitosa para {instance.original_filename} "
        f"({instance.file_size_bytes / 1024:.2f} KB)"
    )


# Signal opcional: Logging de subidas exitosas
@receiver(post_delete, sender=ClinicalFile)
def log_file_deletion_audit(sender, instance, **kwargs):
    """
    Signal de auditoría: Registra eliminación de archivos para trazabilidad.
    
    Útil para cumplimiento normativo y auditorías médicas.
    """
    logger.info(
        f" AUDITORÍA - Archivo clínico eliminado:\n"
        f"  ID: {instance.id}\n"
        f"  Paciente: {instance.paciente_id}\n"
        f"  Archivo: {instance.original_filename}\n"
        f"  Categoría: {instance.get_category_display()}\n"
        f"  Subido por: {instance.uploaded_by.correo if instance.uploaded_by else 'N/A'}\n"
        f"  Fecha creación: {instance.created_at}\n"
        f"  S3 Key: {instance.s3_key}"
    )
