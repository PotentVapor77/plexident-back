from ..models import Usuario

class UserRepository:
    @staticmethod
    def get_all():
        return Usuario.objects.filter(status=True)

    @staticmethod
    def get_by_id(user_id):
        return Usuario.objects.filter(id_usuario=user_id, status=True).first()

    @staticmethod
    def create(**kwargs):
        usuario = Usuario(**kwargs)
        usuario.full_clean()
        usuario.save()
        return usuario

    @staticmethod
    def update(usuario, **kwargs):
        for key, value in kwargs.items():
            setattr(usuario, key, value)
        usuario.full_clean()
        usuario.save()
        return usuario

    @staticmethod
    def soft_delete(usuario):
        usuario.status = False
        usuario.save()
