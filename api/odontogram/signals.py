# odontograma/signals.py
"""
Observer Pattern con Django Signals
Adaptado para la nueva estructura: Catálogo + Instancias de Pacientes
"""

from django.db.models.signals import (
    post_save, pre_save, post_delete, pre_delete, m2m_changed
)
from django.dispatch import receiver, Signal
from django.core.cache import cache
from django.utils import timezone
import logging

from api.odontogram.models import (
    # Catálogo (sin cambios)
    CategoriaDiagnostico,
    Diagnostico,
    AreaAfectada,
    TipoAtributoClinico,
    OpcionAtributoClinico,
    DiagnosticoAreaAfectada,
    DiagnosticoAtributoClinico,
    # Nuevas instancias
    Paciente,
    Diente,
    SuperficieDental,
    DiagnosticoDental,
    HistorialOdontograma,
)
from api.odontogram import models

logger = logging.getLogger(__name__)

# =============================================================================
# SEÑALES PERSONALIZADAS
# =============================================================================

# Señal cuando se crea un diagnóstico crítico en el catálogo
diagnostico_critico_creado = Signal()

# Señal cuando se registra un diagnóstico en un paciente
diagnostico_dental_registrado = Signal()

# Señal cuando se marca un diente como ausente
diente_marcado_ausente = Signal()

# Señal cuando se actualiza el estado de un tratamiento
estado_tratamiento_modificado = Signal()

# =============================================================================
# RECEIVERS PARA CATÁLOGO (Diagnosticos, Atributos, Áreas)
# =============================================================================

@receiver(post_save, sender=Diagnostico)
def log_diagnostico_catalogo_cambios(sender, instance, created, **kwargs):
    """Registra cambios en diagnósticos del catálogo"""
    if created:
        logger.info(
            f"Diagnóstico catálogo creado: {instance.nombre} ({instance.siglas}) - "
            f"Prioridad: {instance.prioridad}"
        )
        if instance.prioridad >= 4:
            diagnostico_critico_creado.send(sender=sender, diagnostico=instance)
    else:
        logger.info(f"Diagnóstico catálogo modificado: {instance.nombre}")

@receiver(post_save, sender=CategoriaDiagnostico)
def log_categoria_cambios(sender, instance, created, **kwargs):
    """Registra cambios en categorías"""
    if created:
        logger.info(
            f"Categoría creada: {instance.nombre} - Prioridad: {instance.prioridad_key}"
        )

@receiver(post_save, sender=TipoAtributoClinico)
def log_atributo_tipo_cambios(sender, instance, created, **kwargs):
    """Registra cambios en tipos de atributos"""
    if created:
        logger.info(f"Tipo de atributo creado: {instance.nombre}")

# =============================================================================
# RECEIVERS PARA INSTANCIAS (DiagnosticoDental, Diente, Superficie)
# =============================================================================

@receiver(post_save, sender=DiagnosticoDental)
def log_diagnostico_dental_guardado(sender, instance, created, **kwargs):
    """Registra cuando se guarda un diagnóstico de paciente"""
    if created:
        logger.info(
            f"Diagnóstico dental registrado: {instance.diagnostico_catalogo.nombre} "
            f"en {instance.superficie.diente.codigo_fdi} "
            f"({instance.superficie.get_nombre_display()}) "
            f"- Paciente: {instance.diente.paciente.nombre_completo}"
        )

        # Emitir señal personalizada
        diagnostico_dental_registrado.send(
            sender=sender,
            diagnostico_dental=instance,
            paciente=instance.diente.paciente
        )

        # Invalidar caché del paciente
        cache.delete(f'odontograma:paciente:{instance.diente.paciente.id}')
    else:
        logger.info(f"Diagnóstico dental modificado: {instance.id}")

@receiver(post_save, sender=Diente)
def log_diente_cambios(sender, instance, created, **kwargs):
    """Registra cambios en dientes de pacientes"""
    if created:
        logger.info(
            f"Diente creado: {instance.codigo_fdi} para paciente {instance.paciente.nombre_completo}"
        )
    elif instance.ausente:
        logger.warning(
            f"Diente {instance.codigo_fdi} marcado como ausente para {instance.paciente.nombre_completo}"
        )

        # Emitir señal
        diente_marcado_ausente.send(sender=sender, diente=instance)

@receiver(post_save, sender=DiagnosticoDental)
def detectar_cambio_estado_tratamiento(sender, instance, created, **kwargs):
    """Detecta cambios en el estado del tratamiento"""
    if not created:
        try:
            old_instance = DiagnosticoDental.objects.get(pk=instance.pk)
            if old_instance.estado_tratamiento != instance.estado_tratamiento:
                logger.info(
                    f"Estado de tratamiento modificado: "
                    f"{old_instance.estado_tratamiento} → {instance.estado_tratamiento}"
                )

                # Emitir señal
                estado_tratamiento_modificado.send(
                    sender=sender,
                    diagnostico_dental=instance,
                    estado_anterior=old_instance.estado_tratamiento,
                    estado_nuevo=instance.estado_tratamiento
                )
        except DiagnosticoDental.DoesNotExist:
            pass

# =============================================================================
# RECEIVERS PARA GESTIÓN DE CACHÉ
# =============================================================================

@receiver(post_save, sender=Diagnostico)
@receiver(post_delete, sender=Diagnostico)
def invalidar_cache_diagnosticos_catalogo(sender, instance, **kwargs):
    """Invalida caché del catálogo cuando se modifica"""
    cache_keys = [
        'odontograma:diagnosticos:all',
        f'odontograma:diagnosticos:categoria:{instance.categoria_id}',
        f'odontograma:diagnosticos:prioridad:{instance.prioridad}',
        'odontograma:config:full',
    ]
    for key in cache_keys:
        cache.delete(key)
    logger.debug(f"Caché invalidado para diagnóstico catálogo: {instance.id}")

@receiver(post_save, sender=DiagnosticoDental)
@receiver(post_delete, sender=DiagnosticoDental)
def invalidar_cache_odontograma_paciente(sender, instance, **kwargs):
    """Invalida caché del odontograma del paciente"""
    cache.delete(f'odontograma:paciente:{instance.diente.paciente.id}')
    cache.delete(f'odontograma:diente:{instance.diente.id}')
    logger.debug(f"Caché invalidado para odontograma: {instance.id}")

@receiver(post_save, sender=CategoriaDiagnostico)
@receiver(post_delete, sender=CategoriaDiagnostico)
def invalidar_cache_categorias(sender, instance, **kwargs):
    """Invalida caché de categorías"""
    cache.delete_pattern('odontograma:categorias:*')
    cache.delete('odontograma:config:full')
    logger.debug("Caché de categorías invalidado")

@receiver(post_save, sender=TipoAtributoClinico)
@receiver(post_delete, sender=TipoAtributoClinico)
@receiver(post_save, sender=OpcionAtributoClinico)
@receiver(post_delete, sender=OpcionAtributoClinico)
def invalidar_cache_atributos(sender, instance, **kwargs):
    """Invalida caché de atributos"""
    cache.delete_pattern('odontograma:atributos:*')
    cache.delete('odontograma:config:full')
    logger.debug("Caché de atributos invalidado")

# =============================================================================
# RECEIVERS PARA VALIDACIONES
# =============================================================================

@receiver(pre_save, sender=Diagnostico)
def validar_diagnostico_catalogo(sender, instance, **kwargs):
    """Valida diagnóstico del catálogo"""
    if not 1 <= instance.prioridad <= 5:
        raise ValueError("La prioridad debe estar entre 1 y 5")

    if instance.pk:
        diagnosticos_existentes = Diagnostico.objects.filter(
            siglas=instance.siglas
        ).exclude(pk=instance.pk)
    else:
        diagnosticos_existentes = Diagnostico.objects.filter(siglas=instance.siglas)

    if diagnosticos_existentes.exists():
        raise ValueError(f"Las siglas '{instance.siglas}' ya están en uso")

@receiver(pre_save, sender=OpcionAtributoClinico)
def validar_opcion_atributo(sender, instance, **kwargs):
    """Valida opción de atributo"""
    if instance.prioridad is not None and not 1 <= instance.prioridad <= 5:
        raise ValueError("La prioridad debe estar entre 1 y 5 o ser NULL")

@receiver(pre_save, sender=DiagnosticoDental)
def validar_diagnostico_dental(sender, instance, **kwargs):
    """Valida diagnóstico dental de paciente"""
    if instance.prioridad_asignada is not None:
        if not 1 <= instance.prioridad_asignada <= 5:
            raise ValueError("Prioridad asignada debe estar entre 1 y 5")

# =============================================================================
# RECEIVERS PARA HISTORIAL Y AUDITORÍA
# =============================================================================

@receiver(post_save, sender=DiagnosticoDental)
def registrar_cambio_diagnostico_dental(sender, instance, created, **kwargs):
    """Registra en historial cuando se agrega/modifica un diagnóstico dental"""
    if created:
        HistorialOdontograma.objects.create(
            diente=instance.diente,
            tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_AGREGADO,
            descripcion=f"{instance.diagnostico_catalogo.nombre} agregado en {instance.superficie.get_nombre_display()}",
            odontologo=instance.odontologo,
            datos_nuevos={
                'diagnostico_id': instance.diagnostico_catalogo.id,
                'superficie': instance.superficie.nombre,
                'atributos': instance.atributos_clinicos,
            }
        )

@receiver(post_delete, sender=DiagnosticoDental)
def registrar_eliminacion_diagnostico_dental(sender, instance, **kwargs):
    """Registra en historial cuando se elimina un diagnóstico dental"""
    HistorialOdontograma.objects.create(
        diente=instance.diente,
        tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_ELIMINADO,
        descripcion=f"{instance.diagnostico_catalogo.nombre} eliminado",
        odontologo=instance.odontologo,
        datos_anteriores={
            'diagnostico_id': instance.diagnostico_catalogo.id,
            'superficie': instance.superficie.nombre,
        }
    )

@receiver(pre_save, sender=Diente)
def registrar_ausencia_diente(sender, instance, **kwargs):
    """Registra cuando se marca un diente como ausente"""
    if instance.pk:
        try:
            old_instance = Diente.objects.get(pk=instance.pk)
            if not old_instance.ausente and instance.ausente:
                # Se marcó como ausente - crear historial cuando se guarde
                pass
        except Diente.DoesNotExist:
            pass

# =============================================================================
# RECEIVERS PARA NOTIFICACIONES
# =============================================================================

@receiver(diagnostico_critico_creado)
def notificar_diagnostico_critico_catalogo(sender, diagnostico, **kwargs):
    """Notifica cuando se crea un diagnóstico crítico en el catálogo"""
    logger.warning(
        f"⚠️  DIAGNÓSTICO CRÍTICO EN CATÁLOGO: {diagnostico.nombre} "
        f"(Prioridad: {diagnostico.prioridad})"
    )

@receiver(diagnostico_dental_registrado)
def notificar_diagnostico_dental_registrado(sender, diagnostico_dental, paciente, **kwargs):
    """Notifica cuando se registra un diagnóstico en un paciente"""
    if diagnostico_dental.prioridad_efectiva >= 4:
        logger.warning(
            f"⚠️  DIAGNÓSTICO CRÍTICO REGISTRADO: {diagnostico_dental.diagnostico_catalogo.nombre} "
            f"en paciente {paciente.nombre_completo}"
        )

@receiver(diente_marcado_ausente)
def notificar_diente_ausente(sender, diente, **kwargs):
    """Notifica cuando se marca un diente como ausente"""
    logger.warning(
        f"⚠️  DIENTE MARCADO COMO AUSENTE: {diente.codigo_fdi} "
        f"- Paciente: {diente.paciente.nombre_completo}"
    )

@receiver(estado_tratamiento_modificado)
def notificar_cambio_estado_tratamiento(sender, diagnostico_dental, estado_anterior, estado_nuevo, **kwargs):
    """Notifica cuando cambia el estado del tratamiento"""
    logger.info(
        f"Estado de tratamiento modificado: {diagnostico_dental.diagnostico_catalogo.nombre} "
        f"{estado_anterior} → {estado_nuevo}"
    )

# =============================================================================
# RECEIVERS PARA INTEGRIDAD DE DATOS
# =============================================================================

@receiver(pre_delete, sender=CategoriaDiagnostico)
def prevenir_eliminacion_categoria_con_diagnosticos(sender, instance, **kwargs):
    """Previene eliminar categoría con diagnósticos"""
    if instance.diagnosticos.exists():
        raise ValueError(
            f"No se puede eliminar '{instance.nombre}' - tiene diagnósticos. "
            f"Desactívela en su lugar."
        )

@receiver(pre_delete, sender=TipoAtributoClinico)
def prevenir_eliminacion_atributo_en_uso(sender, instance, **kwargs):
    """Previene eliminar atributo en uso"""
    if instance.diagnosticos_aplicables.exists():
        raise ValueError(
            f"No se puede eliminar '{instance.nombre}' - está siendo usado. "
            f"Desactívelo en su lugar."
        )

@receiver(pre_delete, sender=Diente)
def prevenir_eliminacion_diente_con_diagnosticos(sender, instance, **kwargs):
    """Previene eliminar diente que tiene diagnósticos"""
    diagnosticos = DiagnosticoDental.objects.filter(
        superficie__diente=instance,
        activo=True
    ).count()
    if diagnosticos > 0:
        raise ValueError(
            f"No se puede eliminar diente {instance.codigo_fdi} - tiene diagnósticos. "
            f"Desactívelo en su lugar."
        )

# =============================================================================
# ESTADÍSTICAS
# =============================================================================

@receiver(post_save, sender=Diagnostico)
@receiver(post_delete, sender=Diagnostico)
def actualizar_estadisticas_catalogo(sender, instance, **kwargs):
    """Actualiza estadísticas del catálogo"""
    stats = {
        'total_diagnosticos': Diagnostico.objects.filter(activo=True).count(),
        'diagnosticos_criticos': Diagnostico.objects.filter(
            activo=True, prioridad__gte=4
        ).count(),
        'ultima_actualizacion': timezone.now().isoformat(),
    }
    cache.set('odontograma:stats:catalogo', stats, timeout=3600)
    logger.debug("Estadísticas del catálogo actualizadas")

@receiver(post_save, sender=DiagnosticoDental)
@receiver(post_delete, sender=DiagnosticoDental)
def actualizar_estadisticas_paciente(sender, instance, **kwargs):
    """Actualiza estadísticas del odontograma del paciente"""
    paciente = instance.diente.paciente
    stats = {
        'total_diagnosticos': DiagnosticoDental.objects.filter(
            superficie__diente__paciente=paciente,
            activo=True
        ).count(),
        'diagnosticos_criticos': DiagnosticoDental.objects.filter(
            superficie__diente__paciente=paciente,
            activo=True
        ).filter(
            models.Q(prioridad_asignada__gte=4) |
            (models.Q(prioridad_asignada__isnull=True) & 
             models.Q(diagnostico_catalogo__prioridad__gte=4))
        ).count(),
        'ultima_actualizacion': timezone.now().isoformat(),
    }
    cache.set(f'odontograma:stats:paciente:{paciente.id}', stats, timeout=3600)
    logger.debug(f"Estadísticas del paciente {paciente.id} actualizadas")