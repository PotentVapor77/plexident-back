from django.contrib.auth.backends import BaseBackend
from .models import Usuario

class UsuarioAuthBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        return Usuario.authenticate(username=username, password=password)

    def get_user(self, user_id):
        try:
            return Usuario.objects.get(pk=user_id, activo=True)
        except Usuario.DoesNotExist:
            return None