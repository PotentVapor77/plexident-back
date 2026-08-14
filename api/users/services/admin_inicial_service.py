# api/users/services/admin_inicial_service.py
"""Servicio central del administrador inicial del sistema.

Garantiza que el usuario administrador por defecto se cree UNA sola vez
durante el primer arranque del sistema y que NO pueda volver a crearse,
ni aunque se fuerce la operación.
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def username_admin_inicial():
    """Username reservado para el administrador inicial."""
    return getattr(settings, 'DEFAULT_ADMIN_USERNAME', 'admin') or 'admin'


def sistema_inicializado():
    """¿El sistema ya fue inicializado (admin inicial ya creado alguna vez)?"""
    from api.users.models import EstadoSistema

    estado = EstadoSistema.objects.first()
    return bool(estado and estado.admin_inicial_creado)


def es_username_admin_inicial_prohibido(username):
    """
    ¿Está prohibido crear un usuario con este username?

    El username del administrador inicial queda 'reservado' de forma
    permanente una vez que el sistema fue inicializado: ni por la API, ni
    por el ORM/shell, ni por comandos forzados puede volver a crearse.
    """
    if not username:
        return False
    if username != username_admin_inicial():
        return False
    return sistema_inicializado()


def marcar_sistema_inicializado():
    """Persiste el marcador de que el administrador inicial ya fue creado."""
    from api.users.models import EstadoSistema

    estado = EstadoSistema.objects.first()
    if estado is None:
        estado = EstadoSistema()
    estado.admin_inicial_creado = True
    estado.save()
    logger.info('Sistema marcado como inicializado (admin inicial creado).')
