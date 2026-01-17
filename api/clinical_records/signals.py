from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from api.clinical_records.models import ClinicalRecord
import logging

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=ClinicalRecord)
def clinical_record_pre_save(sender, instance, **kwargs):
    """
    Signal ejecutado antes de guardar un historial clínico.
    Valida que no se edite un historial cerrado.
    """
    if instance.pk:  # Si ya existe
        try:
            old_instance = ClinicalRecord.objects.get(pk=instance.pk)
            if old_instance.estado == 'CERRADO' and instance.estado == 'CERRADO':
                # Verificar si se está intentando modificar campos además del estado
                if old_instance.observaciones != instance.observaciones:
                    # Permitir agregar observaciones incluso si está cerrado
                    pass
                else:
                    logger.warning(f"Intento de edición de historial cerrado: {instance.id}")
        except ClinicalRecord.DoesNotExist:
            pass


@receiver(post_save, sender=ClinicalRecord)
def clinical_record_post_save(sender, instance, created, **kwargs):
    """
    Signal ejecutado después de guardar un historial clínico.
    Registra la creación o actualización en logs.
    """
    if created:
        logger.info(f"Historial clínico creado: {instance.id} para paciente {instance.paciente.nombre_completo}")
    else:
        logger.info(f"Historial clínico actualizado: {instance.id} - Estado: {instance.estado}")
