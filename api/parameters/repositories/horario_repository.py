# api/parameters/repositories/horario_repository.py
from django.db import transaction
from ..models import ConfiguracionHorario
import logging

logger = logging.getLogger(__name__)


class HorarioRepository:
    """Repositorio para operaciones con horarios"""
    
    @staticmethod
    def get_horario_by_dia(dia_semana: int, activo: bool = True):
        """
        Obtener horario por día de la semana
        
        Args:
            dia_semana: 0=Lunes, 6=Domingo
            activo: Filtrar solo horarios activos
        
        Returns:
            ConfiguracionHorario or None
        """
        try:
            queryset = ConfiguracionHorario.objects
            if activo:
                queryset = queryset.filter(activo=True)
            
            return queryset.get(dia_semana=dia_semana)
        except ConfiguracionHorario.DoesNotExist:
            logger.debug(f"No hay horario configurado para el día {dia_semana}")
            return None
        except Exception as e:
            logger.error(f"Error obteniendo horario: {str(e)}")
            raise
    
    @staticmethod
    def get_horarios_semana(activo: bool = True):
        """
        Obtener todos los horarios de la semana
        
        Args:
            activo: Filtrar solo horarios activos
        
        Returns:
            QuerySet de ConfiguracionHorario ordenado por día
        """
        queryset = ConfiguracionHorario.objects
        if activo:
            queryset = queryset.filter(activo=True)
        
        return queryset.order_by('dia_semana')
    
    @staticmethod
    @transaction.atomic
    def crear_horario(dia_semana: int, apertura, cierre, usuario):
        """
        Crear nuevo horario
        
        Args:
            dia_semana: Día de la semana
            apertura: Hora de apertura
            cierre: Hora de cierre
            usuario: Usuario que crea el registro
        
        Returns:
            ConfiguracionHorario creado
        """
        try:
            if ConfiguracionHorario.objects.filter(dia_semana=dia_semana).exists():
                raise ValueError(f"Ya existe un horario para el día {dia_semana}")
            
            horario = ConfiguracionHorario.objects.create(
                dia_semana=dia_semana,
                apertura=apertura,
                cierre=cierre,
                creado_por=usuario,
                activo=True
            )
            
            logger.info(f"Horario creado: {horario}")
            return horario
            
        except Exception as e:
            logger.error(f"Error creando horario: {str(e)}")
            raise
    
    @staticmethod
    @transaction.atomic
    def actualizar_horario(dia_semana: int, apertura, cierre, usuario, activo: bool = True):
        """
        Actualizar o crear horario
        
        Args:
            dia_semana: Día de la semana
            apertura: Nueva hora de apertura
            cierre: Nueva hora de cierre
            usuario: Usuario que actualiza
            activo: Estado del horario
        
        Returns:
            Tuple (ConfiguracionHorario, created)
        """
        try:
            horario, created = ConfiguracionHorario.objects.update_or_create(
                dia_semana=dia_semana,
                defaults={
                    'apertura': apertura,
                    'cierre': cierre,
                    'activo': activo,
                    'actualizado_por': usuario
                }
            )
            
            action = "creado" if created else "actualizado"
            logger.info(f"Horario {action}: {horario}")
            return horario, created
            
        except Exception as e:
            logger.error(f"Error actualizando horario: {str(e)}")
            raise
    
    @staticmethod
    @transaction.atomic
    def actualizar_horarios_masivo(horarios_data, usuario):
        """
        Actualizar múltiples horarios en una transacción
        
        Args:
            horarios_data: Lista de diccionarios con datos de horarios
            usuario: Usuario que realiza la actualización
        
        Returns:
            Lista de resultados (dict)
        """
        resultados = []
        
        for horario_data in horarios_data:
            dia_semana = horario_data.get('dia_semana')
            apertura = horario_data.get('apertura')
            cierre = horario_data.get('cierre')
            activo = horario_data.get('activo', True)
            
            try:
                horario, created = HorarioRepository.actualizar_horario(
                    dia_semana, apertura, cierre, usuario, activo
                )
                
                resultados.append({
                    'dia_semana': dia_semana,
                    'success': True,
                    'created': created,
                    'horario_id': str(horario.id)
                })
                
            except Exception as e:
                logger.error(f"Error actualizando horario día {dia_semana}: {str(e)}")
                resultados.append({
                    'dia_semana': dia_semana,
                    'success': False,
                    'error': str(e)
                })
        
        return resultados
    
    @staticmethod
    def desactivar_horario(dia_semana: int, usuario):
        """
        Desactivar horario (soft delete)
        
        Args:
            dia_semana: Día a desactivar
            usuario: Usuario que desactiva
        
        Returns:
            True si se desactivó, False si no existía
        """
        try:
            updated = ConfiguracionHorario.objects.filter(
                dia_semana=dia_semana, activo=True
            ).update(
                activo=False,
                actualizado_por=usuario
            )
            
            if updated > 0:
                logger.info(f"Horario día {dia_semana} desactivado por {usuario.username}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error desactivando horario: {str(e)}")
            raise