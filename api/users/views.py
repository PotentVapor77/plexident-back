from rest_framework import viewsets,status,permissions
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from .models import Usuario
from .serializers import UsuarioSerializer, LoginSerializer
from .services.user_service import UserService
from rest_framework_simplejwt.tokens import RefreshToken

class UsuarioViewSet(viewsets.ModelViewSet):
    serializer_class = UsuarioSerializer
    queryset = Usuario.objects.all()
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        data = serializer.validated_data
        UserService.crear_usuario(data)

    def perform_update(self, serializer):
        usuario = get_object_or_404(Usuario, pk=self.kwargs['pk'])
        UserService.actualizar_usuario(usuario, serializer.validated_data)

    def perform_destroy(self, instance):
        UserService.eliminar_usuario(instance)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        
        usuario = Usuario.authenticate(username=username, password=password)
        
        if usuario:
            # Generar token JWT
            refresh = RefreshToken.for_user(usuario)
            usuario_data = UsuarioSerializer(usuario).data
            return Response({
                'success': True,
                'message': 'Login exitoso',
                'user': usuario_data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'message': 'Usuario o contraseña incorrectos'
            }, status=status.HTTP_401_UNAUTHORIZED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
