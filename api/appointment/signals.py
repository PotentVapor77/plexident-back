# api/appointment/signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Cita, EstadoCita, HistorialCita
import logging

logger = logging.getLogger(__name__)
# Diccionario temporal para almacenar datos antes del save
_citas_previas = {}

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

@receiver(pre_save, sender=Cita)
def guardar_estado_anterior(sender, instance, **kwargs):
    """
    RF-05.11: Captura el estado anterior antes de guardar
    """
    if instance.pk:  # Solo si es actualización
        try:
            cita_anterior = Cita.objects.get(pk=instance.pk)
            _citas_previas[str(instance.pk)] = {
                'fecha': str(cita_anterior.fecha),
                'hora_inicio': str(cita_anterior.hora_inicio),
                'hora_fin': str(cita_anterior.hora_fin),
                'duracion': cita_anterior.duracion,
                'odontologo': cita_anterior.odontologo.get_full_name(),
                'odontologo_id': str(cita_anterior.odontologo.id),
                'paciente': cita_anterior.paciente.nombre_completo,
                'estado': cita_anterior.estado,
                'tipo_consulta': cita_anterior.tipo_consulta,
                'motivo_consulta': cita_anterior.motivo_consulta or '',
            }
        except Cita.DoesNotExist:
            pass


@receiver(post_save, sender=Cita)
def registrar_cambio_cita(sender, instance, created, **kwargs):
    """
    RF-05.11: Registra automáticamente los cambios en el historial
    """
    from django_currentuser.middleware import get_current_user
    
    usuario = get_current_user()
    if not usuario:
        logger.warning(f"No se pudo obtener usuario actual para cita {instance.id}")
        return
    
    if created:
        # Creación de cita
        HistorialCita.objects.create(
            cita=instance,
            usuario=usuario,
            accion='CREACION',
            datos_nuevos={
                'fecha': str(instance.fecha),
                'hora_inicio': str(instance.hora_inicio),
                'duracion': instance.duracion,
                'odontologo': instance.odontologo.get_full_name(),
                'paciente': instance.paciente.nombre_completo,
                'estado': instance.estado,
                'tipo_consulta': instance.tipo_consulta,
            },
            descripcion=f"Cita creada para {instance.paciente.nombre_completo}"
        )
        logger.info(f"✅ Historial: Cita {instance.id} creada")
    else:
        # Actualización de cita
        cita_id = str(instance.pk)
        if cita_id in _citas_previas:
            datos_anteriores = _citas_previas[cita_id]
            datos_nuevos = {
                'fecha': str(instance.fecha),
                'hora_inicio': str(instance.hora_inicio),
                'hora_fin': str(instance.hora_fin),
                'duracion': instance.duracion,
                'odontologo': instance.odontologo.get_full_name(),
                'odontologo_id': str(instance.odontologo.id),
                'paciente': instance.paciente.nombre_completo,
                'estado': instance.estado,
                'tipo_consulta': instance.tipo_consulta,
                'motivo_consulta': instance.motivo_consulta or '',
            }
            
            # Determinar el tipo de acción
            accion = 'MODIFICACION'
            descripcion = "Cita modificada"
            
            # Cancelación
            if datos_anteriores['estado'] != EstadoCita.CANCELADA and datos_nuevos['estado'] == EstadoCita.CANCELADA:
                accion = 'CANCELACION'
                descripcion = f"Cita cancelada. Motivo: {instance.motivo_cancelacion}"
            
            # Reprogramación
            elif datos_anteriores['estado'] != EstadoCita.REPROGRAMADA and datos_nuevos['estado'] == EstadoCita.REPROGRAMADA:
                accion = 'REPROGRAMACION'
                descripcion = f"Cita reprogramada de {datos_anteriores['fecha']} {datos_anteriores['hora_inicio']} a {datos_nuevos['fecha']} {datos_nuevos['hora_inicio']}"
            
            # Cambio de estado
            elif datos_anteriores['estado'] != datos_nuevos['estado']:
                accion = 'CAMBIO_ESTADO'
                descripcion = f"Estado cambiado de {datos_anteriores['estado']} a {datos_nuevos['estado']}"
            
            # Cambio de fecha/hora (sin cambiar estado)
            elif (datos_anteriores['fecha'] != datos_nuevos['fecha'] or 
                  datos_anteriores['hora_inicio'] != datos_nuevos['hora_inicio']):
                accion = 'MODIFICACION'
                descripcion = f"Fecha/hora modificada de {datos_anteriores['fecha']} {datos_anteriores['hora_inicio']} a {datos_nuevos['fecha']} {datos_nuevos['hora_inicio']}"
            
            # Crear registro de historial
            HistorialCita.objects.create(
                cita=instance,
                usuario=usuario,
                accion=accion,
                datos_anteriores=datos_anteriores,
                datos_nuevos=datos_nuevos,
                descripcion=descripcion
            )
            
            logger.info(f"✅ Historial: {accion} registrada para cita {instance.id}")
            
            # Limpiar datos temporales
            del _citas_previas[cita_id]