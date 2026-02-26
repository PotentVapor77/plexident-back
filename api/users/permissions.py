# users/permissions.py
from rest_framework.permissions import BasePermission
from .models import PermisoUsuario
import logging

logger = logging.getLogger(__name__)


# Modelos donde cualquier usuario autenticado puede hacer GET,
# independientemente de sus PermisoUsuario registrados.
# Esto permite que Asistentes y Odontólogos puedan cargar
# listas de odontólogos al agendar citas, sin requerir
# permisos administrativos sobre el módulo de usuarios.
MODELOS_LECTURA_LIBRE = {"usuario"}

# Roles operativos que pueden hacer GET en MODELOS_LECTURA_LIBRE
ROLES_LECTURA_LIBRE = {"Odontologo", "Asistente"}


class UserBasedPermission(BasePermission):
    """
    Verifica permisos por usuario/módulo/método HTTP usando PermisoUsuario.
    Se usa junto con IsAuthenticated.

    Regla especial: GET sobre modelos en MODELOS_LECTURA_LIBRE está permitido
    para roles en ROLES_LECTURA_LIBRE, aunque no tengan un PermisoUsuario
    registrado en BD (útil cuando el signal de creación no corrió para
    usuarios anteriores, o para endpoints de solo lectura compartidos).
    """

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        # Administrador tiene acceso completo sin verificar tabla
        if getattr(user, "rol", None) == "Administrador":
            return True

        # Cada ViewSet debe definir permission_model_name
        model_name = getattr(view, "permission_model_name", None)
        if not model_name:
            logger.warning(
                f"{view.__class__.__name__} no define 'permission_model_name'"
            )
            return False

        metodo = request.method  # GET, POST, PUT, PATCH, DELETE
        rol = getattr(user, "rol", None)

        # ── Regla de lectura libre ───────────────────────────────────────────
        # Roles operativos pueden hacer GET en modelos de lectura compartida
        # (ej: Asistente necesita listar odontólogos para agendar citas).
        if metodo == "GET" and model_name in MODELOS_LECTURA_LIBRE and rol in ROLES_LECTURA_LIBRE:
            logger.debug(
                f"Lectura libre permitida: {user.username} ({rol}) → GET {model_name}"
            )
            return True

        # ── Verificación normal por tabla PermisoUsuario ─────────────────────
        try:
            permiso = PermisoUsuario.objects.get(usuario=user, modelo=model_name)
            allowed = metodo in permiso.metodos_permitidos

            if not allowed:
                logger.warning(
                    f"Acceso denegado: {user.username} no tiene permiso "
                    f"{metodo} en {model_name}"
                )

            return allowed

        except PermisoUsuario.DoesNotExist:
            logger.warning(
                f"Sin permisos definidos: usuario={user.username}, "
                f"rol={rol}, modelo={model_name}"
            )
            return False