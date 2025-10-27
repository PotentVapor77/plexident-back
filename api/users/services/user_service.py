from ..repositories.user_repository import UserRepository

class UserService:
    @staticmethod
    def crear_usuario(data):
        return UserRepository.create(**data)

    @staticmethod
    def listar_usuarios():
        return UserRepository.get_all()

    @staticmethod
    def obtener_usuario(id_usuario):
        return UserRepository.get_by_id(id_usuario)

    @staticmethod
    def actualizar_usuario(usuario, data):
        return UserRepository.update(usuario, **data)

    @staticmethod
    def eliminar_usuario(usuario):
        UserRepository.soft_delete(usuario)
