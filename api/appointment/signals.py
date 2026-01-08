# api/appointment/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Cita, EstadoCita
import logging

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Cita)
def cita_pre_save(sender, instance, **kwargs):
    """
    Signal ejecutado antes de guardar una cita
    Realiza validaciones adicionales
    """
    # Si la cita ya existe, obtener el estado anterior
    if instance.pk:
        try:
            cita_anterior = Cita.objects.get(pk=instance.pk)
            
            # Detectar cambio de estado
            if cita_anterior.estado != instance.estado:
                logger.info(
                    f"Cita {instance.id} cambió de estado: "
                    f"{cita_anterior.estado} -> {instance.estado}"
                )
        except Cita.DoesNotExist:
            pass


@receiver(post_save, sender=Cita)
def cita_post_save(sender, instance, created, **kwargs):
    """
    Signal ejecutado después de guardar una cita
    """
    if created:
        logger.info(
            f"Nueva cita creada: {instance.id} - "
            f"Paciente: {instance.paciente.nombre_completo} - "
            f"Odontólogo: {instance.odontologo.get_full_name()} - "
            f"Fecha: {instance.fecha} {instance.hora_inicio}"
        )
    else:
        logger.info(f"Cita {instance.id} actualizada")
        
        # Si la cita fue cancelada
        if instance.estado == EstadoCita.CANCELADA:
            logger.warning(
                f"Cita {instance.id} cancelada. "
                f"Motivo: {instance.motivo_cancelacion}"
            )
        
        # Si la cita fue reprogramada
        if instance.estado == EstadoCita.REPROGRAMADA:
            logger.info(
                f"Cita {instance.id} reprogramada. "
                f"Fecha original: {instance.fecha} {instance.hora_inicio}"
            )
