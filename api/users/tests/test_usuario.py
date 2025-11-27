import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from django.urls import reverse

Usuario = get_user_model()

@pytest.mark.django_db
class TestUsuarioAPI:
    """Test suite para la API de usuarios"""

    def setup_method(self):
        """Configuración inicial para cada test"""
        self.client = APIClient()
        self.user_data = {
            'username': 'juanodonto',
            'nombres': 'Juan',
            'apellidos': 'Pérez',
            'correo': 'juan@test.com',
            'telefono': '1234567890',
            'rol': 'odontologo',
            'password': 'password123',
            'activo': True
        }
        self.admin_user = Usuario.objects.create_user(
            username='adminadmin',
            nombres='Admin',
            apellidos='Sistema',
            correo='admin@test.com',
            telefono='1234567890',
            rol='admin',
            password='admin123',
            activo=True
        )

    def test_crear_usuario_como_admin(self):
        """Test: Admin puede crear usuario"""
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.post(
            reverse('users:users-list'),  # ← CAMBIADO A 'users:users-list'
            data=self.user_data,
            format='json'
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['correo'] == self.user_data['correo']
        assert response.data['rol'] == self.user_data['rol']

    def test_crear_usuario_sin_autenticacion(self):
        """Test: Usuario no autenticado no puede crear usuario"""
        response = self.client.post(
            reverse('users:users-list'),  # ← CAMBIADO A 'users:users-list'
            data=self.user_data,
            format='json'
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_listar_usuarios_como_odontologo(self):
        """Test: Odontólogo solo puede listar usuarios (no crear)"""
        odontologo = Usuario.objects.create_user(
            username='carlodont',
            nombres='Carlos',
            apellidos='Lopez',
            correo='odontologo@test.com',
            telefono='1234567890',
            rol='odontologo',
            password='pass123',
            activo=True
        )
        self.client.force_authenticate(user=odontologo)
        response_create = self.client.post(
            reverse('users:users-list'),  # ← CAMBIADO A 'users:users-list'
            data=self.user_data,
            format='json'
        )
        assert response_create.status_code == status.HTTP_403_FORBIDDEN
        response_list = self.client.get(reverse('users:users-list'))  # ← CAMBIADO
        assert response_list.status_code == status.HTTP_200_OK


    def test_listar_usuarios_como_asistente(self):
        """Test: Asistente solo puede listar usuarios (no crear)"""
        asistente = Usuario.objects.create_user(
            username='carlodont',
            nombres='Manolo',
            apellidos='Lopez',
            correo='asistente@test.com',
            telefono='1234567890',
            rol='asistente',
            password='pass123',
            activo=True
        )
        self.client.force_authenticate(user=asistente)
        response_create = self.client.post(
            reverse('users:users-list'),  # ← CAMBIADO A 'users:users-list'
            data=self.user_data,
            format='json'
        )
        assert response_create.status_code == status.HTTP_403_FORBIDDEN
        response_list = self.client.get(reverse('users:users-list'))  # ← CAMBIADO
        assert response_list.status_code == status.HTTP_200_OK
        

    def test_obtener_usuario_por_id(self):
        """Test: Obtener usuario específico por ID"""
        usuario = Usuario.objects.create_user(
            username='juanodonto2',
            nombres='Juan',
            apellidos='Pérez',
            correo='juan2@test.com',
            telefono='1234567890',
            rol='odontologo',
            password='password123',
            activo=True
        )
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(
            reverse('users:users-detail', kwargs={'pk': usuario.id})  # ← CAMBIADO A 'users:users-detail'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(usuario.id)
        assert response.data['correo'] == usuario.correo

@pytest.mark.django_db
class TestUsuarioPermissions:
    """Tests específicos para permisos por rol"""

    def test_asistente_solo_puede_listar(self):
        asistente = Usuario.objects.create_user(
            username='anaasist',
            nombres='Ana',
            apellidos='Rodriguez',
            correo='asistente@test.com',
            telefono='1234567890',
            rol='asistente',
            password='pass123',
            activo=True
        )
        usuario = Usuario.objects.create_user(
            username='pacientetest',
            nombres='Paciente',
            apellidos='Test',
            correo='paciente@test.com',
            telefono='1234567890',
            rol='asistente',
            password='pass123',
            activo=True
        )
        self.client = APIClient()
        self.client.force_authenticate(user=asistente)
        
        response_list = self.client.get(reverse('users:users-list'))  # ← CAMBIADO
        assert response_list.status_code == status.HTTP_200_OK
        
        response_create = self.client.post(reverse('users:users-list'), data={})  # ← CAMBIADO
        assert response_create.status_code == status.HTTP_403_FORBIDDEN
        
        response_update = self.client.patch(
            reverse('users:users-detail', kwargs={'pk': usuario.id}),  # ← CAMBIADO
            data={'nombres': 'Actualizado'}
        )
        assert response_update.status_code == status.HTTP_403_FORBIDDEN
        
        response_delete = self.client.delete(
            reverse('users:users-detail', kwargs={'pk': usuario.id})  # ← CAMBIADO
        )
        assert response_delete.status_code == status.HTTP_403_FORBIDDEN

# ... (el resto de los tests de TestUsuarioModel se mantienen igual)

# TESTS ADICIONALES PARA USUARIO AUTENTICADO
@pytest.mark.django_db
class TestUsuarioAutenticado:
    """Tests para usuario autenticado (no admin) accediendo a sus propios datos"""

    def setup_method(self):
        """Configuración inicial para cada test"""
        self.client = APIClient()
        self.usuario_autenticado = Usuario.objects.create_user(
            username='miautenticado',
            nombres='Mi',
            apellidos='Usuario',
            correo='miusuario@test.com',
            telefono='1234567890',
            rol='asistente',
            password='pass123',
            activo=True
        )
        self.client.force_authenticate(user=self.usuario_autenticado)

    def test_usuario_autenticado_puede_ver_sus_propios_datos(self):
        """Test: Usuario autenticado puede ver sus propios datos"""
        response = self.client.get(
            reverse('users:users-detail', kwargs={'pk': self.usuario_autenticado.id})
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['correo'] == self.usuario_autenticado.correo
        assert response.data['username'] == self.usuario_autenticado.username

    

    def test_usuario_autenticado_no_puede_cambiar_su_rol(self):
        """Test: Usuario autenticado NO puede cambiar su propio rol"""
        datos_actualizacion = {
            'rol': 'admin'  # Intentar escalar privilegios
        }
        
        response = self.client.patch(
            reverse('users:users-detail', kwargs={'pk': self.usuario_autenticado.id}),
            data=datos_actualizacion,
            format='json'
        )
        
        # Depende de tu implementación, pero el rol no debería cambiar
        self.usuario_autenticado.refresh_from_db()
        assert self.usuario_autenticado.rol == 'asistente'

    def test_usuario_autenticado_no_puede_eliminarse_a_si_mismo(self):
        """Test: Usuario autenticado NO puede eliminarse a sí mismo"""
        response = self.client.delete(
            reverse('users:users-detail', kwargs={'pk': self.usuario_autenticado.id})
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        # Verificar que el usuario sigue activo
        self.usuario_autenticado.refresh_from_db()
        assert self.usuario_autenticado.activo == True

    def test_usuario_autenticado_puede_ver_lista_de_usuarios(self):
        """Test: Usuario autenticado puede ver la lista de usuarios"""
        # Crear otro usuario para verificar que aparece en la lista
        otro_usuario = Usuario.objects.create_user(
            username='otrousuario',
            nombres='Otro',
            apellidos='Usuario',
            correo='otro@test.com',
            telefono='1234567890',
            rol='odontologo',
            password='pass123',
            activo=True
        )
        
        response = self.client.get(reverse('users:users-list'))
        assert response.status_code == status.HTTP_200_OK
        
        # Debería ver al menos los usuarios activos
        assert len(response.data) >= 2

    def test_usuario_autenticado_no_puede_crear_otros_usuarios(self):
        """Test: Usuario autenticado (no admin) NO puede crear otros usuarios"""
        user_data = {
            'username': 'nuevousuario',
            'nombres': 'Nuevo',
            'apellidos': 'Usuario',
            'correo': 'nuevo@test.com',
            'telefono': '1234567890',
            'rol': 'asistente',
            'password': 'password123',
            'activo': True
        }
        
        response = self.client.post(
            reverse('users:users-list'),
            data=user_data,
            format='json'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_usuario_autenticado_no_puede_ver_usuarios_eliminados(self):
        """Test: Usuario autenticado no ve usuarios eliminados (status=False)"""
        # Crear usuario inactivo (eliminado)
        usuario_inactivo = Usuario.objects.create_user(
            username='inactivo',
            nombres='Inactivo', 
            apellidos='Usuario',
            correo='inactivo@test.com',
            telefono='1234567890',
            rol='asistente',
            password='pass123',
            activo=False  # Eliminado
        )
        
        response = self.client.get(reverse('users:users-list'))
        assert response.status_code == status.HTTP_200_OK
        
        # No debería ver el usuario inactivo
        usuarios = response.data
        correos = [usuario['correo'] for usuario in usuarios]
        assert 'inactivo@test.com' not in correos
