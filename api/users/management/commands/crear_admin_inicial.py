# api/users/management/commands/crear_admin_inicial.py
# python manage.py crear_admin_inicial [--quiet] [--force]
import io
import logging
import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from api.users.services.admin_inicial_service import (
    marcar_sistema_inicializado,
    sistema_inicializado,
    username_admin_inicial,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        'Crea el usuario administrador por defecto en el PRIMER arranque del sistema. '
        'Es idempotente y el usuario NO puede volver a crearse ni con --force.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--quiet',
            action='store_true',
            help='No muestra salida detallada (uso automático en migraciones/startup).',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Se ignora: el administrador inicial jamás se vuelve a crear.',
        )

    def handle(self, *args, **options):
        if options.get('quiet'):
            self.stdout = io.StringIO()

        Usuario = get_user_model()

        # =====================================================================
        # 1) ¿Ya se inicializó el sistema? -> no se vuelve a crear NUNCA.
        # =====================================================================
        if sistema_inicializado():
            if options['force']:
                self.stdout.write(self.style.WARNING(
                    'El administrador inicial ya fue creado. '
                    'NO se vuelve a crear (ni aunque se fuerce).'
                ))
            else:
                self.stdout.write(
                    'El administrador inicial ya fue creado. Nada que hacer.'
                )
            return

        username = username_admin_inicial()

        # =====================================================================
        # 2) El username reservado ya existe (ej. BD creada antes de esta
        #    funcionalidad): solo marcamos el sistema como inicializado.
        # =====================================================================
        if Usuario.objects.filter(username=username).exists():
            marcar_sistema_inicializado()
            self.stdout.write(self.style.SUCCESS(
                f'El usuario "{username}" ya existía; el sistema quedó marcado '
                'como inicializado y no se volverá a crear.'
            ))
            return

        # =====================================================================
        # 3) Validar credenciales del entorno
        # =====================================================================
        errores = self._validar_credenciales()
        if errores:
            raise CommandError(
                'No se pudo crear el administrador inicial:\n  - '
                + '\n  - '.join(errores)
            )

        # =====================================================================
        # 4) Crear el admin + marcar inicializado (transacción atómica)
        # =====================================================================
        with transaction.atomic():
            usuario = Usuario.objects.create_superuser(
                username=username,
                correo=settings.DEFAULT_ADMIN_EMAIL,
                password=settings.DEFAULT_ADMIN_PASSWORD,
                nombres=settings.DEFAULT_ADMIN_NOMBRES,
                apellidos=settings.DEFAULT_ADMIN_APELLIDOS,
                telefono=settings.DEFAULT_ADMIN_TELEFONO,
            )
            marcar_sistema_inicializado()

        logger.info(f'Administrador inicial creado: {usuario.username}')
        self.stdout.write(self.style.SUCCESS(
            f'✔ Administrador inicial creado: "{usuario.username}"'
        ))

    def _validar_credenciales(self):
        errores = []

        username = username_admin_inicial()
        if not username or len(username) < 4:
            errores.append(
                'DEFAULT_ADMIN_USERNAME debe tener al menos 4 caracteres.'
            )

        password = getattr(settings, 'DEFAULT_ADMIN_PASSWORD', '')
        if not password:
            errores.append(
                'DEFAULT_ADMIN_PASSWORD es obligatoria (no usar contraseñas vacías).'
            )
        elif len(password) < 8:
            errores.append(
                'DEFAULT_ADMIN_PASSWORD debe tener al menos 8 caracteres.'
            )

        correo = getattr(settings, 'DEFAULT_ADMIN_EMAIL', '')
        if not correo or '@' not in correo:
            errores.append(
                'DEFAULT_ADMIN_EMAIL es obligatorio y debe ser un correo válido.'
            )

        nombres = getattr(settings, 'DEFAULT_ADMIN_NOMBRES', '')
        apellidos = getattr(settings, 'DEFAULT_ADMIN_APELLIDOS', '')
        if not nombres or not apellidos:
            errores.append(
                'DEFAULT_ADMIN_NOMBRES y DEFAULT_ADMIN_APELLIDOS son obligatorios.'
            )

        telefono = getattr(settings, 'DEFAULT_ADMIN_TELEFONO', '')
        if not telefono or not re.match(r'^\d{10,}$', telefono):
            errores.append(
                'DEFAULT_ADMIN_TELEFONO es obligatorio y debe tener al menos '
                '10 dígitos numéricos.'
            )

        return errores
