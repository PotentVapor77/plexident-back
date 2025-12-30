# patients/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Paciente
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Paciente)
def paciente_audit(sender, instance, created, **kwargs):
    """Signal para auditar pacientes - VERSIÓN CORREGIDA"""
    try:
        #  SIMPLIFICADO: usar directamente la propiedad
        nombre = instance.nombre_completo
        
        if created:
            logger.info(f"[AUDIT] Paciente creado: {nombre} (ID: {instance.id})")
            print(f"[AUDIT] Paciente creado: {nombre} (ID: {instance.id})")
        else:
            logger.info(f"[AUDIT] Paciente actualizado: {nombre} (ID: {instance.id})")
            print(f"[AUDIT] Paciente actualizado: {nombre} (ID: {instance.id})")
    except Exception as e:
        logger.error(f"Error en signal paciente_audit: {e}")
        print(f"Error en signal paciente_audit: {e}")
