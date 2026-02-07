# api/parameters/services/horario_service.py
from datetime import time, datetime
from django.utils import timezone
from django.core.cache import cache
from ..repositories.horario_repository import HorarioRepository
import logging

logger = logging.getLogger(__name__)


class HorarioService:
    """Servicio de lógica de negocio para horarios"""
    
    # Cache keys
    CACHE_KEY_HORARIOS_SEMANA = 'horarios_semana_activos'
    CACHE_DURATION = 300
    
    @staticmethod
    def validar_horario(apertura: time, cierre: time) -> tuple[bool, str]:
        """
        Validar que un horario sea lógico y razonable
        
        Args:
            apertura: Hora de apertura
            cierre: Hora de cierre
        
        Returns:
            Tuple (es_valido, mensaje_error)
        """
        if apertura >= cierre:
            return False, "La hora de apertura debe ser anterior a la de cierre"
        
        if apertura < time(5, 0):
            return False, "La hora de apertura no puede ser antes de las 5:00 AM"
        
        if cierre > time(23, 0):
            return False, "La hora de cierre no puede ser después de las 11:00 PM"
        
        duracion_horas = (cierre.hour - apertura.hour) + (cierre.minute - apertura.minute) / 60
        if duracion_horas < 1:
            return False, "La duración mínima de atención debe ser 1 hora"
        
        if duracion_horas > 16:
            return False, "La duración máxima de atención no puede exceder 16 horas"
        
        return True, ""
    
    @staticmethod
    def es_horario_laboral(fecha_hora=None, incluir_cache=True) -> bool:
        """
        Verificar si una fecha/hora está dentro del horario laboral
        
        Args:
            fecha_hora: Fecha y hora a verificar (default: ahora)
            incluir_cache: Usar cache para mejorar rendimiento
        
        Returns:
            True si es horario laboral
        """
        if not fecha_hora:
            fecha_hora = timezone.now()
        
        if incluir_cache:
            cache_key = f"es_horario_laboral_{fecha_hora.date()}_{fecha_hora.hour}"
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        
        dia_semana = fecha_hora.weekday()
        hora_actual = fecha_hora.time()
        
        horario = HorarioRepository.get_horario_by_dia(dia_semana)
        
        if not horario or not horario.activo:
            resultado = False
        else:
            resultado = horario.apertura <= hora_actual <= horario.cierre
        
        if incluir_cache:
            cache.set(cache_key, resultado, 300)
        
        return resultado