# users/permissions.py

from rest_framework.permissions import BasePermission
from .models import  PermisoUsuario
import logging

logger = logging.getLogger(__name__)



# api/users/permissions.py - ACTUALIZAR

class UserBasedPermission(BasePermission):
    """
    Verifica permisos por usuario/módulo/método HTTP usando PermisoUsuario.
    Se usa junto con IsAuthenticated.
    """

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        # Admin tiene acceso completo
        if getattr(user, "rol", None) == "Administrador":
            return True

        # Cada ViewSet debe definir permission_model_name = 'usuario', 'paciente', etc.
        model_name = getattr(view, "permission_model_name", None)
        if not model_name:
            logger.warning(f"{view.__class__.__name__} no define 'permission_model_name'")
            return False

        metodo = request.method  # GET, POST, PUT, PATCH, DELETE


        
        try:
            # Buscar permiso específico del usuario
            permiso = PermisoUsuario.objects.get(usuario=user, modelo=model_name)
            allowed = metodo in permiso.metodos_permitidos
            
            if not allowed:
                logger.warning(
                    f"Acceso denegado: {user.username} no tiene permiso {metodo} en {model_name}"
                )
            
            return allowed
            
        except PermisoUsuario.DoesNotExist:
            # Si no existe el permiso, denegar acceso
            logger.warning(
                f"Sin permisos definidos: usuario={user.username}, rol={user.rol}, modelo={model_name}"
            )
            return False