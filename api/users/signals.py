from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)

Usuario = get_user_model()


# =============================================================================
# PERMISOS POR DEFECTO POR ROL
# =============================================================================

DEFAULT_PERMISSIONS = {
    # Odontólogo: acceso completo a su área clínica
    "Odontologo": [
        # Pacientes: CRUD completo
        {"modelo": "paciente",              "metodos_permitidos": ["GET", "POST", "PUT", "PATCH"]},
        # Agenda: CRUD completo
        {"modelo": "agenda",                "metodos_permitidos": ["GET", "POST", "PUT", "PATCH", "DELETE"]},
        # Odontograma y componentes
        {"modelo": "odontograma",           "metodos_permitidos": ["GET", "POST", "PUT", "PATCH", "DELETE"]},
        {"modelo": "historialodontograma",  "metodos_permitidos": ["GET", "POST", "PUT", "PATCH", "DELETE"]},
        {"modelo": "diente",                "metodos_permitidos": ["GET", "POST", "PUT", "PATCH", "DELETE"]},
        {"modelo": "diagnosticodental",     "metodos_permitidos": ["GET", "POST", "PUT", "PATCH", "DELETE"]},
        {"modelo": "superficie",            "metodos_permitidos": ["GET", "POST", "PUT", "PATCH", "DELETE"]},
        # Historia clínica: CRUD completo
        {"modelo": "historia_clinica",      "metodos_permitidos": ["GET", "POST", "PUT", "PATCH", "DELETE"]},
        {"modelo": "clinicalfile",          "metodos_permitidos": ["GET", "POST", "DELETE"]},
        # Usuarios: solo lectura (necesario para ver quién creó registros)
        {"modelo": "usuario",               "metodos_permitidos": ["GET"]},
    ],

    # Asistente: solo agenda + vista de pacientes
    "Asistente": [
        # Pacientes: solo lectura y creación (sin edición avanzada ni borrado)
        {"modelo": "paciente",              "metodos_permitidos": ["GET", "POST", "PUT", "PATCH"]},
        # Agenda: CRUD completo (es su responsabilidad principal)
        {"modelo": "agenda",                "metodos_permitidos": ["GET", "POST", "PUT", "PATCH", "DELETE"]},
        # Odontograma: solo lectura
        {"modelo": "odontograma",           "metodos_permitidos": ["GET"]},
        {"modelo": "historialodontograma",  "metodos_permitidos": ["GET"]},
        {"modelo": "diente",                "metodos_permitidos": ["GET"]},
        {"modelo": "diagnosticodental",     "metodos_permitidos": ["GET"]},
        {"modelo": "superficie",            "metodos_permitidos": ["GET"]},
        # Historia clínica: solo lectura
        {"modelo": "historia_clinica",      "metodos_permitidos": ["GET"]},
        {"modelo": "clinicalfile",          "metodos_permitidos": ["GET"]},
        # Usuarios: sin acceso
        {"modelo": "usuario",               "metodos_permitidos": ["GET"]},
    ],
}


# =============================================================================
# SIGNAL: configurar is_staff / is_superuser según rol
# =============================================================================

@receiver(pre_save, sender=Usuario)
def set_auth_permissions(sender, instance, **kwargs):
    """
    Configura permisos ANTES de guardar — evita bucle infinito.
    """
    if instance.rol == "Administrador":
        instance.is_staff = True
        instance.is_superuser = True
    elif instance.rol == "Odontologo":
        instance.is_staff = True
        instance.is_superuser = False
    else:
        instance.is_staff = False
        instance.is_superuser = False

    # Activar admin automáticamente al crear
    if not instance.pk and instance.rol == "Administrador":
        instance.is_active = True


# =============================================================================
# SIGNAL: logging al crear usuario
# =============================================================================

@receiver(post_save, sender=Usuario)
def log_usuario_creado(sender, instance, created, **kwargs):
    """Solo logging — no modifica nada."""
    if created:
        logger.info(f"Usuario creado: {instance.username} — Rol: {instance.rol}")


# =============================================================================
# SIGNAL: crear permisos por defecto según rol
# =============================================================================

@receiver(post_save, sender=Usuario)
def crear_permisos_por_defecto(sender, instance, created, **kwargs):
    """
    Crea permisos por defecto cuando se crea un usuario no-Administrador.
    Usa get_or_create para ser idempotente (seguro ante re-ejecuciones).
    """
    if not created:
        return

    rol = instance.rol

    # Administradores tienen acceso total via UserBasedPermission —
    # no necesitan registros en PermisoUsuario.
    if rol == "Administrador":
        return

    permisos_del_rol = DEFAULT_PERMISSIONS.get(rol)
    if not permisos_del_rol:
        logger.warning(
            f"No hay permisos por defecto definidos para el rol '{rol}' "
            f"(usuario: {instance.username})"
        )
        return

    from api.users.models import PermisoUsuario

    permisos_creados = []
    for permiso_config in permisos_del_rol:
        permiso, was_created = PermisoUsuario.objects.get_or_create(
            usuario=instance,
            modelo=permiso_config["modelo"],
            defaults={"metodos_permitidos": permiso_config["metodos_permitidos"]},
        )
        if was_created:
            permisos_creados.append(permiso_config["modelo"])
            logger.info(
                f"✔ Permiso creado — usuario: {instance.username}, "
                f"modelo: '{permiso_config['modelo']}', "
                f"métodos: {permiso_config['metodos_permitidos']}"
            )

    if permisos_creados:
        logger.info(
            f"🔑 Permisos por defecto creados para '{instance.username}' ({rol}): "
            f"{', '.join(permisos_creados)}"
        )