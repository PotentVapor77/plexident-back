# authentication/services/auth_service.py
from api.users.models import Usuario


class AuthService:
    @staticmethod
    def authenticate_user(username: str, password: str):
        """Autentica un usuario y lo retorna si es válido"""
        try:
            usuario = Usuario.objects.get(username=username, activo=True)
            if usuario.check_password(password) and usuario.is_active:
                return usuario
        except Usuario.DoesNotExist:
            return None
        return None
    
    @staticmethod
    def get_current_user(user_id: str):
        """Obtener usuario actual por ID"""
        try:
            #  Acceso directo sin repositorio
            return Usuario.objects.get(pk=user_id, activo=True, is_active=True)
        except Usuario.DoesNotExist:
            return None
    
    @staticmethod
    def get_user_by_username(username: str):
        """Obtener usuario por username"""
        try:
            return Usuario.objects.get(username=username, activo=True, is_active=True)
        except Usuario.DoesNotExist:
            return None
