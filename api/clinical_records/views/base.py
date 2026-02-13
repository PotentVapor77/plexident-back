# api/clinical_records/views/base.py
"""
Mixins y configuración base para ViewSets de historiales clínicos
"""
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)


class ClinicalRecordPagination(PageNumberPagination):
    """
    Paginación personalizada para historiales clínicos
    - 35 elementos por página por defecto
    - Permite al cliente ajustar el tamaño
    - Incluye información detallada de paginación
    """
    page_size = 35 
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        """
        Respuesta paginada con información adicional
        """
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'page_size': self.page_size,
            'results': data
        })


class BasePermissionMixin:
    """
    Mixin para permisos base
    """
    permission_classes = [IsAuthenticated]


class QuerysetOptimizationMixin:
    """
    Optimiza queries con select_related y prefetch_related
    """
    RELATED_FIELDS = []
    PREFETCH_FIELDS = []
    
    def get_queryset(self):
        """
        Optimiza el queryset con relaciones precargadas
        """
        queryset = super().get_queryset()
        
        if self.RELATED_FIELDS:
            queryset = queryset.select_related(*self.RELATED_FIELDS)
        
        if self.PREFETCH_FIELDS:
            queryset = queryset.prefetch_related(*self.PREFETCH_FIELDS)
        
        return queryset


class SearchFilterMixin:
    """
    Permite buscar por:
    - Nombre del paciente (nombres, apellidos, nombre completo)
    - Cédula del paciente
    - Motivo de consulta
    - Enfermedad actual
    - Observaciones
    - Nombre del odontólogo
    - Número de historia clínica
    - Número de archivo
    """
    search_fields = [
        # Paciente
        'paciente__nombres',
        'paciente__apellidos',
        'paciente__nombre_completo',
        'paciente__cedula_pasaporte',
        
        # Campos del historial
        'motivo_consulta',
        'enfermedad_actual',
        'observaciones',
        'numero_historia_clinica_unica',
        'numero_archivo',
        
        # Odontólogo
        'odontologo_responsable__nombres',
        'odontologo_responsable__apellidos',
    ]
    
    def get_queryset(self):
        """
        Aplica búsqueda con Q objects para mejor rendimiento
        """
        queryset = super().get_queryset()
        search_query = self.request.query_params.get('search', None)
        
        if search_query:
            # Búsqueda con OR en múltiples campos
            q_objects = Q()
            for field in self.search_fields:
                q_objects |= Q(**{f"{field}__icontains": search_query})
            
            queryset = queryset.filter(q_objects).distinct()
        
        return queryset


class DateRangeFilterMixin:
    """
    
    Parámetros:
    - fecha_desde: Fecha inicial (YYYY-MM-DD)
    - fecha_hasta: Fecha final (YYYY-MM-DD)
    """
    
    def get_queryset(self):
        """
        Aplica filtros de fecha si están presentes
        """
        queryset = super().get_queryset()
        
        fecha_desde = self.request.query_params.get('fecha_desde', None)
        fecha_hasta = self.request.query_params.get('fecha_hasta', None)
        
        if fecha_desde:
            queryset = queryset.filter(fecha_atencion__gte=fecha_desde)
        
        if fecha_hasta:
            queryset = queryset.filter(fecha_atencion__lte=fecha_hasta)
        
        return queryset


class ActiveFilterMixin:
    """
    Filtra registros activos/inactivos
    """
    
    def get_queryset(self):
        """
        Filtra por estado activo si no se especifica lo contrario
        """
        queryset = super().get_queryset()
        
        # Por defecto, solo mostrar activos
        activo = self.request.query_params.get('activo', 'true')
        
        if activo.lower() == 'true':
            queryset = queryset.filter(activo=True)
        elif activo.lower() == 'false':
            queryset = queryset.filter(activo=False)
        # Si es 'all', no filtra
        
        return queryset


class LoggingMixin:
    """
    Logging automático de acciones
    """
    
    def perform_create(self, serializer):
        """
        Log al crear
        """
        instance = serializer.save()
        logger.info(
            f"Historial clínico creado: {instance.id} por "
            f"{self.request.user.username}"
        )
        return instance
    
    def perform_update(self, serializer):
        """
        Log al actualizar
        """
        instance = serializer.save()
        logger.info(
            f"Historial clínico actualizado: {instance.id} por "
            f"{self.request.user.username}"
        )
        return instance
    
    def perform_destroy(self, instance):
        """
        Log al eliminar (borrado lógico)
        """
        instance.activo = False
        instance.save()
        logger.info(
            f"Historial clínico eliminado (lógico): {instance.id} por "
            f"{self.request.user.username}"
        )
        
    def log_create(self, instance, user):
        """Registra creación de historial"""
        logger.info(
            f"Historial clínico {instance.id} creado por {user.username}"
        )

    def log_update(self, instance, user):
        """Registra actualización de historial"""
        logger.info(
            f"Historial clínico {instance.id} actualizado por {user.username}"
        )

    def log_delete(self, instance, user):
        """Registra eliminación lógica de historial"""
        logger.info(
            f"Historial clínico {instance.id} eliminado (lógicamente) por {user.username}"
        )

    def log_error(self, action, error, user):
        """Registra errores en operaciones"""
        logger.error(
            f"Error en {action} por {user.username}: {str(error)}",
            exc_info=True
        )


# Importación necesaria
from rest_framework.response import Response