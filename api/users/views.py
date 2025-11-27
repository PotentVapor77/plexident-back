from rest_framework import viewsets,status,permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import Usuario
from .serializers import UsuarioSerializer, LoginSerializer
from rest_framework_simplejwt.tokens import RefreshToken
import traceback
from api.permissions import TienePermisoPorRolConfigurable
from django.conf import settings

class UsuarioViewSet(viewsets.ModelViewSet):
    serializer_class = UsuarioSerializer
    permission_classes = [TienePermisoPorRolConfigurable]  
    #permission_classes = [IsAuthenticated]  
    
    def get_queryset(self):
        """Queryset base para todos los usuarios activos"""
        return Usuario.objects.filter(activo=True)

    def list(self, request, *args, **kwargs):
        """Listar usuarios - VERSIÓN CORREGIDA"""
        try:
            print("🔍 Solicitando lista de usuarios...")
            
            # Usar el queryset base
            queryset = self.get_queryset()
            print(f"📊 Usuarios encontrados: {queryset.count()}")
            
            # Serializar los datos
            serializer = self.get_serializer(queryset, many=True)
            
            print("✅ Lista de usuarios generada exitosamente")
            return Response(serializer.data)
            
        except Exception as e:
            print(f"❌ ERROR en listar usuarios: {str(e)}")
            print(f"🔴 Traceback completo: {traceback.format_exc()}")
            
            return Response(
                {
                    'error': 'Error interno del servidor',
                    'detail': str(e),
                    'traceback': traceback.format_exc() if settings.DEBUG else None
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
