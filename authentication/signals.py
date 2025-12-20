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
    # Configurar is_staff e is_superuser según rol (EN ESPAÑOL)
    if instance.rol == 'Administrador':  
        instance.is_staff = True
        instance.is_superuser = True
    elif instance.rol == 'Odontologo': 
        instance.is_superuser = False
    else:  # Asistente u otros
        instance.is_staff = False
        instance.is_superuser = False
    
    # Si es nuevo usuario y es admin, activarlo
    if not instance.pk and instance.rol == 'Administrador':  
        instance.is_active = True
        instance.activo = True  #  Sincronizar ambos campos


@receiver(post_save, sender=Usuario)
def log_usuario_creado(sender, instance, created, **kwargs):
    """
    Solo para logging - NO modifica nada
    """
    if created:
        logger.info(f" Usuario creado: {instance.username} - Rol: {instance.rol}")
