# api/permissions.py
from rest_framework import permissions

class TienePermisoPorRolConfigurable(permissions.BasePermission):
    """
    Permiso configurable por modelo con configuración para múltiples apps
    Sistema de permisos basado en roles para el sistema odontológico
    """
    
    # Definir todos los permisos como atributo de clase
    PERMISOS = {
        # === APP: AUTENTICACIÓN Y AUTORIZACIÓN ===
        'group': {
            'admin': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
            'odontologo': ['GET'],
            'asistente': ['GET']
        },

        
        # === APP: Permiso solo para PACIENTES ===
        'paciente': {
            'admin': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
            'odontologo': ['GET', 'POST', 'PUT', 'PATCH'],
            'asistente': ['GET', 'POST', 'PUT']
        },
        
        
    }
    
    # Permisos solo para usuarios principales, como admin,odon,asistente
    PERMISOS_BASE = {
        'admin': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
        'odontologo': ['GET'],
        'asistente': ['GET']
    }

    def has_permission(self, request, view):
        """
        Verifica si el usuario tiene permiso para realizar la acción
        """
        user = request.user
        
        # Usuario no autenticado no tiene acceso
        if not user.is_authenticated:
            return False
            
        # Admin tiene acceso total a todo
        if user.rol == 'admin':
            return True
        
        # Obtener nombre del modelo desde la vista
        model_name = self._get_model_name(view)
        
        # Buscar permisos específicos para este modelo, usar base si no existe
        permisos_modelo = self.PERMISOS.get(model_name, self.PERMISOS_BASE)
        
        # Verificar si el método HTTP está permitido para el rol del usuario
        metodo_permitido = request.method in permisos_modelo.get(user.rol, [])
        
        return metodo_permitido
    
    
    def _get_model_name(self, view):
        """
        Obtiene el nombre del modelo desde la vista
        """
        try:
            # Intentar obtener desde el queryset
            if hasattr(view, 'queryset') and view.queryset is not None:
                return view.queryset.model._meta.model_name
            
            # Intentar desde el modelo directo
            if hasattr(view, 'model') and view.model is not None:
                return view.model._meta.model_name
            
            # Intentar desde get_queryset
            if hasattr(view, 'get_queryset'):
                queryset = view.get_queryset()
                if queryset is not None:
                    return queryset.model._meta.model_name
            
            # Si no se puede determinar, usar nombre de la clase de vista
            view_name = view.__class__.__name__.lower()
            # Limpiar el nombre
            for suffix in ['viewset', 'view', 'api']:
                if view_name.endswith(suffix):
                    view_name = view_name[:-len(suffix)]
            return view_name.strip('_')
            
        except Exception:
            # Fallback: usar nombre de la vista
            view_name = view.__class__.__name__.lower()
            for suffix in ['viewset', 'view', 'api']:
                if view_name.endswith(suffix):
                    view_name = view_name[:-len(suffix)]
            return view_name.strip('_')


# Permisos adicionales específicos
class EsAdmin(permissions.BasePermission):
    """Permiso que solo permite acceso a administradores"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.rol == 'admin'


class EsOdontologoOAdmin(permissions.BasePermission):
    """Permiso que permite acceso a odontólogos y administradores"""
    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated and user.rol in ['admin', 'odontologo']


class EsAsistenteOAdmin(permissions.BasePermission):
    """Permiso que permite acceso a asistentes y administradores"""
    def has_permission(self, request, view):
        user = request.user
        return user.is_authenticated and user.rol in ['admin', 'asistente']


class SoloLectura(permissions.BasePermission):
    """Permiso que solo permite métodos de lectura (GET, HEAD, OPTIONS)"""
    def has_permission(self, request, view):
        return request.method in permissions.SAFE_METHODS