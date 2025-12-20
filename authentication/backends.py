from django.contrib.auth.backends import BaseBackend
from api.users.models import Usuario  # ← Ya está correcto

class UsuarioAuthBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            usuario = Usuario.objects.get(username=username)
            if usuario.check_password(password) and usuario.is_active:
                return usuario
        except Usuario.DoesNotExist:
            return None
        return None

    def get_user(self, user_id):
        try:
            return Usuario.objects.get(pk=user_id, is_active=True)
        except Usuario.DoesNotExist:
            return None