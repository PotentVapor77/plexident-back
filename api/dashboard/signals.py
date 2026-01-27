# api/dashboard/signals.py

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from api.patients.models.paciente import Paciente
from api.patients.models.constantes_vitales import ConstantesVitales
from api.appointment.models import Cita
import logging

logger = logging.getLogger(__name__)


# ==================== SIGNALS PARA LOGGING ====================

@receiver(post_save, sender=Paciente)
def paciente_creado_signal(sender, instance, created, **kwargs):
    """
    Signal cuando se crea un nuevo paciente
    Útil para invalidar caché del dashboard o enviar notificaciones
    """
    if created:
        logger.info(f"[DASHBOARD] Nuevo paciente registrado: {instance.nombres} {instance.apellidos} (ID: {instance.id})")


@receiver(post_save, sender=ConstantesVitales)
def signos_vitales_registrados_signal(sender, instance, created, **kwargs):
    """
    Signal cuando se registran signos vitales
    Útil para alertas de signos vitales anormales
    """
    if created:
        alertas = []
        
        # Validar temperatura
        if instance.temperatura and instance.temperatura > 37.5:
            alertas.append(f"Temperatura alta: {instance.temperatura}°C")
        
        # Validar pulso
        if instance.pulso:
            if instance.pulso > 100:
                alertas.append(f"Pulso alto: {instance.pulso} lpm")
            elif instance.pulso < 60:
                alertas.append(f"Pulso bajo: {instance.pulso} lpm")
        
        # Validar frecuencia respiratoria
        if instance.frecuencia_respiratoria:
            if instance.frecuencia_respiratoria > 20:
                alertas.append(f"FR alta: {instance.frecuencia_respiratoria} rpm")
            elif instance.frecuencia_respiratoria < 12:
                alertas.append(f"FR baja: {instance.frecuencia_respiratoria} rpm")
        
        if alertas:
            paciente_nombre = f"{instance.paciente.nombres} {instance.paciente.apellidos}"
            logger.warning(
                f"[DASHBOARD ALERTA] Paciente {paciente_nombre}: "
                f"{', '.join(alertas)}"
            )


@receiver(post_save, sender=Cita)
def cita_creada_actualizada_signal(sender, instance, created, **kwargs):
    """
    Signal cuando se crea o actualiza una cita
    Útil para actualizar métricas del dashboard en tiempo real
    """
    if created:
        logger.info(
            f"[DASHBOARD] Nueva cita registrada: "
            f"Paciente {instance.paciente.nombres} {instance.paciente.apellidos}, "
            f"Fecha: {instance.fecha}, Estado: {instance.estado}"
        )
    else:
        # Si cambió el estado, registrarlo
        if hasattr(instance, '_old_estado') and instance._old_estado != instance.estado:
            logger.info(
                f"[DASHBOARD] Cambio de estado de cita {instance.id}: "
                f"{instance._old_estado} → {instance.estado}"
            )


# ==================== PREPARAR INSTANCE PARA TRACKING ====================

@receiver(post_save, sender=Cita)
def track_estado_anterior(sender, instance, **kwargs):
    """Guarda el estado anterior para detectar cambios"""
    if instance.pk:
        try:
            old_instance = Cita.objects.get(pk=instance.pk)
            instance._old_estado = old_instance.estado
        except Cita.DoesNotExist:
            instance._old_estado = None
