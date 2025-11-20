from ..models import Usuario

class AuthService:
    @staticmethod
    def authenticate_user(username, password):
        """Autentica un usuario y lo retorna si es válido"""
        return Usuario.authenticate(username=username, password=password)
    
    @staticmethod
    def create_user_with_password(user_data, password):
        """Crea un usuario con contraseña hasheada"""
        from ..repositories.user_repository import UserRepository
        
        # Crear el usuario sin guardar aún
        usuario = Usuario(**user_data)
        usuario.set_password(password)
        
        # Validar y guardar
        usuario.full_clean()
        usuario.save()
        return usuario