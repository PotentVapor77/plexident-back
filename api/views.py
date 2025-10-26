from rest_framework import viewsets
from django.contrib.auth.models import User
from .serializers import UserSerializer

class UserViewSet(viewsets.ModelViewSet):
    """
    Vista que permite listar, crear, editar y eliminar usuarios.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
