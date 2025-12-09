from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import Usuario
from .serializers import UsuarioSerializer, LoginSerializer, UsuarioCreateSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from api.utils.response_formatter import (
    success_response, 
    error_response, 
    validation_error_response
)
from api.permissions import TienePermisoPorRolConfigurable

class UsuarioViewSet(viewsets.ModelViewSet):
    serializer_class = UsuarioSerializer
    permission_classes = [TienePermisoPorRolConfigurable]
    
    def get_queryset(self):
        """Queryset base para todos los usuarios activos"""
        return Usuario.objects.filter(activo=True)

    def get_serializer_class(self):
        if self.action == 'create':
            return UsuarioCreateSerializer
        return UsuarioSerializer

    def list(self, request, *args, **kwargs):
        """Listar usuarios con formato estandarizado"""
        try:
            print("🔍 Solicitando lista de usuarios...")
            
            # Usar el queryset base
            queryset = self.get_queryset()
            print(f"📊 Usuarios encontrados: {queryset.count()}")
            
            # Serializar los datos
            serializer = self.get_serializer(queryset, many=True)
            
            print("✅ Lista de usuarios generada exitosamente")
            
            # ✅ FORMATO ESTANDARIZADO
            return success_response(
                message="Lista de usuarios obtenida exitosamente",
                data=serializer.data
            )
            
        except Exception as e:
            print(f"❌ ERROR en listar usuarios: {str(e)}")
            
            # ✅ FORMATO ESTANDARIZADO PARA ERRORES
            return error_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                error_type="Internal Server Error",
                message="Error al obtener la lista de usuarios"
            )

    def create(self, request, *args, **kwargs):
        """Crear usuario con formato estandarizado"""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            # ✅ FORMATO ESTANDARIZADO PARA ERRORES DE VALIDACIÓN
            return validation_error_response(
                serializer_errors=serializer.errors,
                message="Error al crear el usuario"
            )
        
        try:
            usuario = serializer.save()
            
            # ✅ FORMATO ESTANDARIZADO
            return success_response(
                message="Usuario creado exitosamente",
                data=UsuarioSerializer(usuario).data,
                status_code=status.HTTP_201_CREATED
            )
        except Exception as e:
            return error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                error_type="Bad Request",
                message=str(e)
            )

    def retrieve(self, request, *args, **kwargs):
        """Obtener usuario específico"""
        try:
            usuario = self.get_object()
            serializer = self.get_serializer(usuario)
            
            # ✅ FORMATO ESTANDARIZADO
            return success_response(
                message="Usuario obtenido exitosamente",
                data=serializer.data
            )
        except Exception:
            return error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                error_type="Not Found",
                message="Usuario no encontrado"
            )

    def update(self, request, *args, **kwargs):
        """Actualizar usuario"""
        usuario = self.get_object()
        serializer = self.get_serializer(usuario, data=request.data, partial=True)
        
        if not serializer.is_valid():
            return validation_error_response(
                serializer_errors=serializer.errors,
                message="Error al actualizar el usuario"
            )
        
        try:
            serializer.save()
            
            # ✅ FORMATO ESTANDARIZADO
            return success_response(
                message="Usuario actualizado exitosamente",
                data=serializer.data
            )
        except Exception as e:
            return error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                error_type="Bad Request",
                message=str(e)
            )

    def destroy(self, request, *args, **kwargs):
        """Desactivar usuario"""
        try:
            usuario = self.get_object()
            usuario.activo = False
            usuario.save()
            
            # ✅ FORMATO ESTANDARIZADO
            return success_response(
                message="Usuario desactivado exitosamente",
                status_code=status.HTTP_204_NO_CONTENT
            )
        except Exception:
            return error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                error_type="Not Found",
                message="Usuario no encontrado"
            )

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def profile(self, request):
        """Obtener perfil del usuario actual"""
        usuario_data = UsuarioSerializer(request.user).data
        
        # ✅ FORMATO ESTANDARIZADO
        return success_response(
            message="Perfil obtenido exitosamente",
            data=usuario_data
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """Login con formato estandarizado"""
    serializer = LoginSerializer(data=request.data)
    
    if not serializer.is_valid():
        # ✅ FORMATO ESTANDARIZADO PARA ERRORES DE VALIDACIÓN
        return validation_error_response(
            serializer_errors=serializer.errors,
            message="Error en los datos de login"
        )
    
    username = serializer.validated_data['username']
    password = serializer.validated_data['password']
    
    usuario = Usuario.authenticate(username=username, password=password)
    
    if usuario:
        # Generar token JWT
        refresh = RefreshToken.for_user(usuario)
        usuario_data = UsuarioSerializer(usuario).data
        
        # ✅ FORMATO ESTANDARIZADO
        return success_response(
            message="Login exitoso",
            data={
                'user': usuario_data,
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                }
            }
        )
    else:
        # ✅ FORMATO ESTANDARIZADO PARA ERRORES
        return error_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_type="Unauthorized",
            message="Usuario o contraseña incorrectos"
        )