"""
Mixins y utilidades compartidas para ViewSets
"""
import logging
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from api.users.permissions import UserBasedPermission

logger = logging.getLogger(__name__)


class ClinicalRecordPagination(PageNumberPagination):
    """Configuración de paginación para módulos clínicos"""
    
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class BasePermissionMixin:
    """Mixin para permisos estándar de módulos clínicos"""
    
    permission_classes = [IsAuthenticated, UserBasedPermission]


class QuerysetOptimizationMixin:
    """Mixin para optimización de querysets con select_related"""
    
    def get_optimized_queryset(self, queryset, related_fields):
        """
        Optimiza el queryset con select_related
        
        Args:
            queryset: QuerySet base
            related_fields: Lista de campos relacionados
            
        Returns:
            QuerySet optimizado
        """
        return queryset.select_related(*related_fields)


class SearchFilterMixin:
    """Mixin para búsqueda en campos comunes"""
    
    def apply_search_filter(self, queryset, search_term, search_fields):
        """
        Aplica filtros de búsqueda OR a múltiples campos
        
        Args:
            queryset: QuerySet base
            search_term: Término de búsqueda
            search_fields: Lista de campos para buscar (notación lookup)
            
        Returns:
            QuerySet filtrado
        """
        from django.db.models import Q
        
        if not search_term:
            return queryset
        
        q_objects = Q()
        for field in search_fields:
            q_objects |= Q(**{f"{field}__icontains": search_term})
        
        return queryset.filter(q_objects)


class ActiveFilterMixin:
    """Mixin para filtrado de registros activos/inactivos"""
    
    def apply_active_filter(self, queryset, request):
        """
        Filtra por estado activo según parámetro de query
        
        Args:
            queryset: QuerySet base
            request: Request object
            
        Returns:
            QuerySet filtrado
        """
        activo_param = request.query_params.get('activo')
        
        if activo_param is not None:
            activo = activo_param.lower() == 'true'
            return queryset.filter(activo=activo)
        
        # Por defecto, solo registros activos
        return queryset.filter(activo=True)


class LoggingMixin:
    """Mixin para logging consistente de operaciones CRUD"""
    
    def log_create(self, instance, user):
        """Log de creación de instancia"""
        logger.info(
            f"{self.__class__.__name__}: "
            f"Creado {instance._meta.model_name} {instance.id} "
            f"por {user.username}"
        )
    
    def log_update(self, instance, user):
        """Log de actualización de instancia"""
        logger.info(
            f"{self.__class__.__name__}: "
            f"Actualizado {instance._meta.model_name} {instance.id} "
            f"por {user.username}"
        )
    
    def log_delete(self, instance, user):
        """Log de eliminación de instancia"""
        logger.info(
            f"{self.__class__.__name__}: "
            f"Eliminado {instance._meta.model_name} {instance.id} "
            f"por {user.username}"
        )
    
    def log_error(self, operation, error, user=None):
        """Log de error en operación"""
        user_info = f"Usuario: {user.username}" if user else "Sin usuario"
        logger.error(
            f"{self.__class__.__name__}: "
            f"Error en {operation}: {str(error)} - {user_info}"
        )
