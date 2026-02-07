# api/parameters/permissions.py
from rest_framework.permissions import BasePermission
from api.users.models import Usuario
import logging

logger = logging.getLogger(__name__)


class ParametroPermission(BasePermission):
    """
    Permisos específicos para el módulo de parámetros.
    Reglas:
    1. Administradores: Acceso completo (CRUD)
    2. Odontólogos: Solo lectura (GET)
    3. Asistentes: Solo lectura (GET)
    """
    
    def has_permission(self, request, view):
        user = request.user
        
        if not user or not user.is_authenticated:
            return False
        
        # Administradores tienen acceso completo
        if user.rol == 'Administrador':
            return True
        
        # Odontólogos y Asistentes solo pueden leer
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            if user.rol in ['Odontologo', 'Asistente']:
                return True
        
        logger.warning(
            f"Acceso denegado a parámetros: {user.username} (rol={user.rol}) "
            f"intentó {request.method} en {view.__class__.__name__}"
        )
        return False
    
    def has_object_permission(self, request, view, obj):
        # Mismo permiso que a nivel de vista
        return self.has_permission(request, view)