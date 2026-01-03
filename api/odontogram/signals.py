# api/odontogram/signals.py
"""
Observer Pattern con Django Signals
Adaptado para la nueva estructura: Catálogo + Instancias de Pacientes
COMPATIBLE CON: patients/models.py (usa nombres y apellidos separados)
"""

from django.db.models.signals import (
    post_save, pre_save, post_delete, pre_delete, m2m_changed
)
from django.dispatch import receiver, Signal
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Q
import logging
from django.contrib.auth import get_user_model

from api.odontogram.models import (
    # Catálogo
    CategoriaDiagnostico,
    Diagnostico,
    AreaAfectada,
    TipoAtributoClinico,
    OpcionAtributoClinico,
    DiagnosticoAreaAfectada,
    DiagnosticoAtributoClinico,
    # Instancias
    Diente,
    SuperficieDental,
    DiagnosticoDental,
    HistorialOdontograma,
)


logger = logging.getLogger(__name__)

Usuario = get_user_model()
# =============================================================================
# FUNCIÓN AUXILIAR: Obtener nombre completo del paciente
# =============================================================================

def get_paciente_nombre_completo(paciente):
    """
    Obtiene el nombre completo del paciente de forma segura.
    Compatible con el modelo Paciente que tiene campos separados:
    - nombres
    - apellidos
    """
    if not paciente:
        return "Paciente desconocido"

    nombres = (paciente.nombres or "").strip()
    apellidos = (paciente.apellidos or "").strip()

    if nombres and apellidos:
        return f"{nombres} {apellidos}"
    elif nombres:
        return nombres
    elif apellidos:
        return apellidos
    else:
        return f"Paciente (ID: {paciente.id})"


# =============================================================================
# FUNCIÓN AUXILIAR PARA CACHÉ SEGURO
# =============================================================================

def safe_delete_pattern(pattern):
    """
    Intenta usar delete_pattern solo si está disponible (Redis).
    En desarrollo con LocMemCache, simplemente ignora el error.
    """
    try:
        cache.delete_pattern(pattern)
    except (AttributeError, NotImplementedError):
        # LocMemCache no soporta delete_pattern - ignorar en desarrollo
        logger.debug(f"delete_pattern no disponible para patrón: {pattern}")


# =============================================================================
# SEÑALES PERSONALIZADAS
# =============================================================================

diagnostico_critico_creado = Signal()
diagnostico_dental_registrado = Signal()
diente_marcado_ausente = Signal()
estado_tratamiento_modificado = Signal()


# =============================================================================
# RECEIVERS PARA CATÁLOGO
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
# RECEIVERS PARA INSTANCIAS - CORRECCIÓN APLICADA
# =============================================================================

@receiver(post_save, sender=DiagnosticoDental)
def log_diagnostico_dental_guardado(sender, instance, created, **kwargs):
    """Registra cuando se guarda un diagnóstico de paciente"""
    if created:
        # CORRECCIÓN: usar helper function para obtener nombre completo
        paciente = instance.superficie.diente.paciente
        paciente_nombre = get_paciente_nombre_completo(paciente)

        logger.info(
            f"Diagnóstico dental registrado: {instance.diagnostico_catalogo.nombre} "
            f"en {instance.superficie.diente.codigo_fdi} "
            f"({instance.superficie.get_nombre_display()}) "
            f"- Paciente: {paciente_nombre}"
        )

        diagnostico_dental_registrado.send(
            sender=sender,
            diagnostico_dental=instance,
            paciente=paciente
        )

        # Invalidar caché del paciente
        cache.delete(f'odontograma:paciente:{paciente.id}')
    else:
        logger.info(f"Diagnóstico dental modificado: {instance.id}")


@receiver(post_save, sender=Diente)
def log_diente_cambios(sender, instance, created, **kwargs):
    """Registra cambios en dientes de pacientes"""
    paciente = instance.paciente
    paciente_nombre = get_paciente_nombre_completo(paciente)

    if created:
        logger.info(
            f"Diente creado: {instance.codigo_fdi} para paciente {paciente_nombre}"
        )
    elif instance.ausente:
        logger.warning(
            f"Diente {instance.codigo_fdi} marcado como ausente para {paciente_nombre}"
        )
        diente_marcado_ausente.send(sender=sender, diente=instance)


@receiver(post_save, sender=DiagnosticoDental)
def detectar_cambio_estado_tratamiento(sender, instance, created, **kwargs):
    """Detecta cambios en el estado del tratamiento"""
    if not created:
        try:
            # Obtener valores originales de la base de datos
            old_instance = DiagnosticoDental.objects.filter(pk=instance.pk).values(
                'estado_tratamiento'
            ).first()

            if old_instance:
                old_estado = old_instance['estado_tratamiento']
                new_estado = instance.estado_tratamiento

                if old_estado != new_estado:
                    logger.info(
                        f"Cambio de estado en DiagnosticoDental {instance.pk}: "
                        f"{old_estado} -> {new_estado}"
                    )

                    estado_tratamiento_modificado.send(
                        sender=sender,
                        diagnostico_dental=instance,
                        estado_anterior=old_estado,
                        estado_nuevo=new_estado
                    )
        except Exception as e:
            logger.error(f"Error detectando cambio de estado: {str(e)}")


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
    paciente_id = instance.superficie.diente.paciente.id
    diente_id = instance.superficie.diente.id

    cache.delete(f'odontograma:paciente:{paciente_id}')
    cache.delete(f'odontograma:diente:{diente_id}')
    logger.debug(f"Caché invalidado para odontograma: {instance.id}")


@receiver(post_save, sender=CategoriaDiagnostico)
@receiver(post_delete, sender=CategoriaDiagnostico)
def invalidar_cache_categorias(sender, instance, **kwargs):
    """Invalida caché de categorías"""
    safe_delete_pattern('odontograma:categorias:*')
    cache.delete('odontograma:config:full')
    logger.debug("Caché de categorías invalidado")


@receiver(post_save, sender=TipoAtributoClinico)
@receiver(post_delete, sender=TipoAtributoClinico)
@receiver(post_save, sender=OpcionAtributoClinico)
@receiver(post_delete, sender=OpcionAtributoClinico)
def invalidar_cache_atributos(sender, instance, **kwargs):
    """Invalida caché de atributos"""
    safe_delete_pattern('odontograma:atributos:*')
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
"""
@receiver(post_save, sender=DiagnosticoDental)
def registrar_cambio_diagnostico_dental(sender, instance, created, **kwargs):
    Registra en historial cuando se agrega un diagnóstico dental
    if created:
        HistorialOdontograma.objects.create(
            diente=instance.superficie.diente,
            tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_AGREGADO,
            descripcion=f"{instance.diagnostico_catalogo.nombre} agregado en {instance.superficie.get_nombre_display()}",
            odontologo=instance.odontologo,
            datos_nuevos={
                'diagnostico_id': instance.diagnostico_catalogo.id,
                'superficie': instance.superficie.nombre,
                'atributos': instance.atributos_clinicos,
            }
        )
 """
 
"""
@receiver(post_delete, sender=DiagnosticoDental)
def registrar_eliminacion_diagnostico_dental(sender, instance, **kwargs):
    Registra en historial cuando se elimina un diagnóstico dental
    HistorialOdontograma.objects.create(
        diente=instance.superficie.diente,
        tipo_cambio=HistorialOdontograma.TipoCambio.DIAGNOSTICO_ELIMINADO,
        descripcion=f"{instance.diagnostico_catalogo.nombre} eliminado",
        odontologo=instance.odontologo,
        datos_anteriores={
            'diagnostico_id': instance.diagnostico_catalogo.id,
            'superficie': instance.superficie.nombre,
        }
    )

"""

@receiver(pre_save, sender=Diente)
def registrar_ausencia_diente(sender, instance, **kwargs):
    """Registra cuando se marca un diente como ausente"""
    if instance.pk:
        try:
            old_instance = Diente.objects.get(pk=instance.pk)
            if not old_instance.ausente and instance.ausente:
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
        f"⚠️ DIAGNÓSTICO CRÍTICO EN CATÁLOGO: {diagnostico.nombre} "
        f"(Prioridad: {diagnostico.prioridad})"
    )


@receiver(diagnostico_dental_registrado)
def notificar_diagnostico_dental_registrado(sender, diagnostico_dental, paciente, **kwargs):
    """Notifica cuando se registra un diagnóstico en un paciente"""
    if diagnostico_dental.prioridad_efectiva >= 4:
        paciente_nombre = get_paciente_nombre_completo(paciente)
        logger.warning(
            f"⚠️ DIAGNÓSTICO CRÍTICO REGISTRADO: {diagnostico_dental.diagnostico_catalogo.nombre} "
            f"en paciente {paciente_nombre}"
        )


@receiver(diente_marcado_ausente)
def notificar_diente_ausente(sender, diente, **kwargs):
    """Notifica cuando se marca un diente como ausente"""
    paciente_nombre = get_paciente_nombre_completo(diente.paciente)
    logger.warning(
        f"⚠️ DIENTE MARCADO COMO AUSENTE: {diente.codigo_fdi} "
        f"- Paciente: {paciente_nombre}"
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
    paciente = instance.superficie.diente.paciente
    stats = {
        'total_diagnosticos': DiagnosticoDental.objects.filter(
            superficie__diente__paciente=paciente,
            activo=True
        ).count(),
        'diagnosticos_criticos': DiagnosticoDental.objects.filter(
            superficie__diente__paciente=paciente,
            activo=True
        ).filter(
            Q(prioridad_asignada__gte=4) |
            (Q(prioridad_asignada__isnull=True) &
            Q(diagnostico_catalogo__prioridad__gte=4))
        ).count(),
        'ultima_actualizacion': timezone.now().isoformat(),
    }
    cache.set(f'odontograma:stats:paciente:{paciente.id}', stats, timeout=3600)
    logger.debug(f"Estadísticas del paciente {paciente.id} actualizadas")



@receiver(post_save, sender=HistorialOdontograma)
def invalidar_cache_historial(sender, instance, **kwargs):
    """Invalida cachés relacionados cuando se crea historial"""
    paciente_id = instance.diente.paciente.id
    version_id = instance.version_id
    
    # Invalidar cachés
    cache.delete(f'historial:versiones:{paciente_id}')
    cache.delete(f'historial:stats:{paciente_id}')
    cache.delete(f'odontograma:completo:{paciente_id}')
    cache.delete(f'odontograma:paciente:{paciente_id}')
    
    logger.debug(f"Caché invalidado para historial paciente {paciente_id}")