# api/users/tests/test_admin_inicial.py
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from api.users.models import EstadoSistema

Usuario = get_user_model()

ADMIN_ENV = {
    'DEFAULT_ADMIN_USERNAME': 'admin',
    'DEFAULT_ADMIN_PASSWORD': 'AdminPass#2026',
    'DEFAULT_ADMIN_EMAIL': 'admin@famysalud.com',
    'DEFAULT_ADMIN_NOMBRES': 'Administrador',
    'DEFAULT_ADMIN_APELLIDOS': 'Sistema',
    'DEFAULT_ADMIN_TELEFONO': '0999999999',
}


def _estado():
    estado = EstadoSistema.objects.first()
    return estado.admin_inicial_creado if estado else False


@pytest.mark.django_db
class TestCrearAdminInicial:
    """Pruebas del comando crear_admin_inicial."""

    @override_settings(**ADMIN_ENV)
    def test_crea_admin_inicial_en_primer_arranque(self):
        call_command('crear_admin_inicial')

        admin = Usuario.objects.get(username='admin')
        assert admin.rol == 'Administrador'
        assert admin.is_staff is True
        assert admin.is_superuser is True
        assert admin.is_active is True
        assert admin.check_password('AdminPass#2026')
        assert _estado() is True

    @override_settings(**ADMIN_ENV)
    def test_no_se_duplica_al_reintentar(self):
        call_command('crear_admin_inicial')
        call_command('crear_admin_inicial')
        call_command('crear_admin_inicial')

        assert Usuario.objects.filter(username='admin').count() == 1

    @override_settings(**ADMIN_ENV)
    def test_no_se_recrea_ni_con_force_aunque_borren_al_usuario(self):
        call_command('crear_admin_inicial')
        Usuario.objects.get(username='admin').delete()

        call_command('crear_admin_inicial', force=True)

        assert Usuario.objects.filter(username='admin').exists() is False
        assert _estado() is True

    @override_settings(**ADMIN_ENV)
    def test_manager_rechaza_username_reservado(self):
        call_command('crear_admin_inicial')
        Usuario.objects.get(username='admin').delete()

        with pytest.raises(PermissionError):
            Usuario.objects.create_superuser(
                username='admin',
                correo='otro@test.com',
                nombres='Otro',
                apellidos='Admin',
                telefono='0999999999',
                password='AdminPass#2026',
            )

    @override_settings(**ADMIN_ENV)
    def test_manager_permite_otros_administradores(self):
        call_command('crear_admin_inicial')

        otro = Usuario.objects.create_superuser(
            username='admin2',
            correo='admin2@test.com',
            nombres='Otro',
            apellidos='Admin',
            telefono='0999999999',
            password='AdminPass#2026',
        )
        assert otro.rol == 'Administrador'

    @override_settings(DEFAULT_ADMIN_PASSWORD='')
    def test_falla_sin_password(self):
        with pytest.raises(CommandError):
            call_command('crear_admin_inicial')
        assert Usuario.objects.filter(username='admin').exists() is False

    @override_settings(**ADMIN_ENV)
    def test_marca_inicializado_si_el_usuario_ya_existia(self):
        Usuario.objects.create_superuser(
            username='admin',
            correo='legacy@test.com',
            nombres='Legacy',
            apellidos='Admin',
            telefono='0999999999',
            password='Legacy#2026',
        )

        call_command('crear_admin_inicial')

        assert _estado() is True
        assert Usuario.objects.filter(username='admin').count() == 1


@pytest.mark.django_db
class TestGuardiaSerializer:
    """La API no puede reutilizar el username reservado del admin inicial."""

    @override_settings(**ADMIN_ENV)
    def test_api_rechaza_username_reservado(self):
        call_command('crear_admin_inicial')
        admin = Usuario.objects.get(username='admin')
        admin.delete()

        client = APIClient()
        otro_admin = Usuario.objects.create_superuser(
            username='rootadmin',
            correo='root@test.com',
            nombres='Root',
            apellidos='Admin',
            telefono='0999999999',
            password='Root#2026',
        )
        client.force_authenticate(user=otro_admin)

        response = client.post(
            '/api/users/usuarios/',
            data={
                'username': 'admin',
                'nombres': 'Nuevo',
                'apellidos': 'Admin',
                'correo': 'nuevo@test.com',
                'telefono': '0999999999',
                'rol': 'Administrador',
                'password': 'Nuevo#2026',
            },
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert Usuario.objects.filter(username='admin').exists() is False
