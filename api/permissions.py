# api/permissions.py
from rest_framework import permissions


class TienePermisoPorRolConfigurable(permissions.BasePermission):
    """
    Sistema de permisos basado en roles para el sistema odontológico.
    
    Uso:
        permission_classes = [TienePermisoPorRolConfigurable]
    
    Los permisos se configuran por modelo y rol.
    Si un modelo no tiene configuración específica, usa PERMISOS_BASE.
    """
    
    # ============================================================================
    # CONFIGURACIÓN DE PERMISOS POR MODELO
    # ============================================================================
    PERMISOS = {
        # === MÓDULO: USUARIOS ===
        'usuario': {
            'Administrador': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
            'Odontologo': ['GET'],
            'Asistente': ['GET']
        },
        
        # === MÓDULO: PACIENTES ===
        'paciente': {
            'Administrador': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
            'Odontologo': ['GET', 'POST', 'PUT', 'PATCH'],
            'Asistente': ['GET', 'POST', 'PUT']
        },
        
    
    }
    
    # ============================================================================
    # PERMISOS POR DEFECTO (para modelos sin configuración específica)
    # ============================================================================
    PERMISOS_BASE = {
        'Administrador': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
        'Odontologo': ['GET'],
        'Asistente': ['GET']
    }

    def has_permission(self, request, view):
        """
        Verifica si el usuario tiene permiso para realizar la acción.
        
        Returns:
            bool: True si tiene permiso, False en caso contrario
        """
        user = request.user
        
        # 1. Usuario no autenticado = sin acceso
        if not user.is_authenticated:
            return False
        
        # 2. Administrador = acceso total
        if user.rol == 'Administrador':
            return True
        
        # 3. Obtener nombre del modelo
        model_name = self._get_model_name(view)
        
        # 4. Buscar permisos específicos o usar base
        permisos_modelo = self.PERMISOS.get(model_name, self.PERMISOS_BASE)
        
        # 5. Verificar si el método HTTP está permitido
        metodos_permitidos = permisos_modelo.get(user.rol, [])
        
        return request.method in metodos_permitidos
    
    def _get_model_name(self, view):
        """
        Extrae el nombre del modelo desde la vista.
        
        Intenta en orden:
        1. view.queryset.model._meta.model_name
        2. view.model._meta.model_name
        3. view.get_queryset().model._meta.model_name
        4. Nombre de la clase de vista (fallback)
        
        Returns:
            str: Nombre del modelo en minúsculas
        """
        try:
            # Opción 1: Desde queryset
            if hasattr(view, 'queryset') and view.queryset is not None:
                return view.queryset.model._meta.model_name
            
            # Opción 2: Desde modelo directo
            if hasattr(view, 'model') and view.model is not None:
                return view.model._meta.model_name
            
            # Opción 3: Desde get_queryset()
            if hasattr(view, 'get_queryset'):
                queryset = view.get_queryset()
                if queryset is not None:
                    return queryset.model._meta.model_name
            
            # Fallback: limpiar nombre de la clase
            return self._clean_view_name(view.__class__.__name__)
            
        except Exception:
            return self._clean_view_name(view.__class__.__name__)
    
    def _clean_view_name(self, view_name):
        """
        Limpia el nombre de la vista para obtener el modelo.
        
        Ejemplo:
            'UsuarioViewSet' -> 'usuario'
            'PacienteAPIView' -> 'paciente'
        
        Args:
            view_name (str): Nombre de la clase de vista
            
        Returns:
            str: Nombre limpio en minúsculas
        """
        view_name = view_name.lower()
        
        # Remover sufijos comunes
        for suffix in ['viewset', 'view', 'api']:
            if view_name.endswith(suffix):
                view_name = view_name[:-len(suffix)]
        
        return view_name.strip('_')
