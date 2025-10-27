from rest_framework import viewsets
from django.shortcuts import get_object_or_404
from .models import Usuario
from .serializers import UsuarioSerializer
from .services.user_service import UserService

class UsuarioViewSet(viewsets.ModelViewSet):
    serializer_class = UsuarioSerializer
    queryset = Usuario.objects.all()

    def perform_create(self, serializer):
        data = serializer.validated_data
        UserService.crear_usuario(data)

    def perform_update(self, serializer):
        usuario = get_object_or_404(Usuario, pk=self.kwargs['pk'])
        UserService.actualizar_usuario(usuario, serializer.validated_data)

    def perform_destroy(self, instance):
        UserService.eliminar_usuario(instance)
