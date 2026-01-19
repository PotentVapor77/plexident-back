from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)

Usuario = get_user_model()


@receiver(pre_save, sender=Usuario)
def set_auth_permissions(sender, instance, **kwargs):
    """
    Configura permisos ANTES de guardar - EVITA BUCLE INFINITO
    """
    #  Configurar is_staff e is_superuser según rol ACTUALIZADO
    if instance.rol == 'Administrador':
        instance.is_staff = True
        instance.is_superuser = True
    elif instance.rol == 'Odontologo':
        instance.is_staff = True
        instance.is_superuser = False
    else:
        instance.is_staff = False
        instance.is_superuser = False
    
    # Si es nuevo usuario y es admin, activarlo
    if not instance.pk and instance.rol == 'Administrador':
        instance.is_active = True


@receiver(post_save, sender=Usuario)
def log_usuario_creado(sender, instance, created, **kwargs):
    """
    Solo para logging - NO modifica nada
    """
    if created:
        logger.info(f"Usuario creado: {instance.username} - Rol: {instance.rol}")
        
        
        

@receiver(post_save, sender=Usuario)
def crear_permisos_default_odontologo(sender, instance, created, **kwargs):
    """
    Crea permisos por defecto cuando se crea un usuario con rol Odontólogo.
    Se ejecuta DESPUÉS de guardar para evitar problemas de integridad.
    """
    # Solo para usuarios nuevos con rol Odontólogo
    if not created:
        return
    
    if instance.rol != 'Odontologo':
        return
    
    from api.users.models import PermisoUsuario
    
    # Definir permisos por defecto para odontólogos
    permisos_default = [
        {
            'modelo': 'paciente',
            'metodos_permitidos': ['GET', 'POST', 'PUT', 'PATCH']
        },
        {
            'modelo': 'historialodontograma',
            'metodos_permitidos': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']  # ← ACTUALIZADO
        },
        {
            'modelo': 'diente',
            'metodos_permitidos': ['GET', 'POST', 'PUT', 'PATCH']
        },
        {
            'modelo': 'diagnosticodental',
            'metodos_permitidos': ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
        },
        # Agregar más modelos según sea necesario
        {
            'modelo': 'superficie',
            'metodos_permitidos': ['GET', 'POST', 'PUT', 'PATCH']
        },
        {
            'modelo': 'clinicalfile',
            'metodos_permitidos': ['GET', 'POST', 'DELETE']
        },
    ]
    
    # Crear cada permiso
    permisos_creados = []
    for permiso_config in permisos_default:
        permiso, created_permiso = PermisoUsuario.objects.get_or_create(
            usuario=instance,
            modelo=permiso_config['modelo'],
            defaults={
                'metodos_permitidos': permiso_config['metodos_permitidos']
            }
        )
        
        if created_permiso:
            permisos_creados.append(permiso_config['modelo'])
            logger.info(
                f"✓ Permiso creado para {instance.username}: "
                f"modelo='{permiso_config['modelo']}', "
                f"métodos={permiso_config['metodos_permitidos']}"
            )
    
    if permisos_creados:
        logger.info(
            f"🔐 Permisos creados automáticamente para odontólogo '{instance.username}': "
            f"{', '.join(permisos_creados)}"
        )
        
