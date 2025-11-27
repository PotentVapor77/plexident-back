from ..models import Usuario

class UserRepository:
    @staticmethod
    def get_all():
        return Usuario.objects.filter(activo=True)

    @staticmethod
    def get_by_id(user_id):
        return Usuario.objects.filter(id=user_id, activo=True).first()

    @staticmethod
    def get_by_username(username):
        return Usuario.objects.filter(username=username, activo=True).first()

    @staticmethod
    def create(**kwargs):
        # Extraer password si existe para manejarlo separadamente
        password = kwargs.pop('password', None)
        usuario = Usuario(**kwargs)
        
        if password:
            usuario.set_password(password)
            
        usuario.full_clean()
        usuario.save()
        return usuario

    @staticmethod
    def update(usuario, **kwargs):
        # Manejar password separadamente si está presente
        password = kwargs.pop('password', None)
        
        for key, value in kwargs.items():
            setattr(usuario, key, value)
            
        if password:
            usuario.set_password(password)
            
        usuario.full_clean()
        usuario.save()
        return usuario

    @staticmethod
    def soft_delete(usuario):
        usuario.activo = False
        usuario.save()