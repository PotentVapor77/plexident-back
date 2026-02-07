from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from api.clinical_records.models import ClinicalRecord
import logging

from api.clinical_records.services.form033_storage_service import Form033StorageService

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=ClinicalRecord)
def clinical_record_pre_save(sender, instance, **kwargs):
    """
    Signal ejecutado antes de guardar un historial clínico.
    Valida que no se edite un historial cerrado.
    """
    if instance.pk: 
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
        
        
@receiver(post_save, sender=ClinicalRecord)
def crear_snapshot_form033_automaticamente(sender, instance, created, **kwargs):
    """
    Signal que crea automáticamente un snapshot del Form033 
    cuando se crea un nuevo historial clínico.
    """
    if created and instance.activo:
        try:
            # Verificar si ya existe un snapshot (evitar duplicados)
            if hasattr(instance, 'form033_snapshot') and instance.form033_snapshot:
                logger.info(f"Snapshot Form033 ya existe para HC {instance.id}")
                return
            
            # Crear snapshot automáticamente
            snapshot = Form033StorageService.crear_snapshot_desde_paciente(
                historial_clinico=instance,
                usuario=instance.odontologo_responsable,
                observaciones='Snapshot automático al crear historial clínico'
            )
            
            logger.info(
                f"Snapshot Form033 creado automáticamente para HC "
                f"{instance.numero_historia_clinica_unica}: {snapshot.id}"
            )
            
        except Exception as e:
            logger.error(
                f"Error creando snapshot automático para HC {instance.id}: {str(e)}",
                exc_info=True
            )
            
@receiver(pre_save, sender=ClinicalRecord)
def validar_piezas_indicadores_antes_guardar(sender, instance, **kwargs):
    """
    Valida que haya piezas suficientes si se están asignando indicadores.
    
    FIX BRECHA 2: Ahora detecta y logea cuando pieza original + suplente
    están ambos ausentes.
    """
    if instance.indicadores_salud_bucal:
        from api.odontogram.services.piezas_service import PiezasIndiceService
        
        info_piezas = PiezasIndiceService.obtener_informacion_piezas(
            str(instance.paciente_id)
        )
        
        piezas_disponibles = info_piezas['estadisticas']['total_piezas']
        
        if piezas_disponibles < 3:
            logger.warning(
                f"HC {instance.id}: Solo {piezas_disponibles} piezas disponibles "
                f"para indicadores (mínimo: 3)"
            )
        
        # Log de suplentes
        suplentes = [
            f"{codigo} → {info['codigo_usado']}"
            for codigo, info in info_piezas['piezas_mapeo'].items()
            if info.get('es_alternativa', False)
        ]
        
        if suplentes:
            logger.info(
                f"HC {instance.id}: Indicadores con piezas suplentes: {', '.join(suplentes)}"
            )
        
        ambos_ausentes = [
            codigo
            for codigo, info in info_piezas['piezas_mapeo'].items()
            if info.get('ambos_ausentes', False) or (
                not info.get('disponible', True) 
                and not info.get('es_alternativa', False)
                and info.get('codigo_usado') is None
            )
        ]
        
        if ambos_ausentes:
            logger.warning(
                f"HC {instance.id}: Piezas sin disponibilidad (original + suplente ausentes): "
                f"{', '.join(ambos_ausentes)}"
            )