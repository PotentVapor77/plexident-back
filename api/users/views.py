# users/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .models import Usuario
from .serializers import (
    UsuarioSerializer,
    UsuarioCreateSerializer,
    UsuarioUpdateSerializer
)
from api.permissions import TienePermisoPorRolConfigurable
import logging

logger = logging.getLogger(__name__)

class UsuarioPagination(PageNumberPagination):
    """Configuración de paginación para usuarios"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class UsuarioViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión de usuarios.
    Los códigos de estado HTTP y formato de respuesta se manejan automáticamente:
    - 200 OK: GET exitoso
    - 201 CREATED: POST exitoso
    - 204 NO CONTENT: DELETE exitoso
    - 400 BAD REQUEST: Datos inválidos
    - 403 FORBIDDEN: Sin permisos
    - 404 NOT FOUND: Recurso no encontrado
    - 500 INTERNAL SERVER ERROR: Error del servidor
    """
    serializer_class = UsuarioSerializer
    permission_classes = [TienePermisoPorRolConfigurable]
    pagination_class = UsuarioPagination

    def get_queryset(self):
        """
        Queryset base que filtra usuarios activos.
        Usa select_related solo para relaciones ForeignKey/OneToOne.
        """
        # ELIMINADO 'rol' porque no es una ForeignKey
        return Usuario.objects.filter(
            activo=True
        ).select_related(
            'creado_por',
            'actualizado_por'
        ).order_by('-fecha_creacion')

    def get_serializer_class(self):
        """Retorna el serializer apropiado según la acción"""
        if self.action == 'create':
            return UsuarioCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UsuarioUpdateSerializer
        return UsuarioSerializer

    def perform_destroy(self, instance):
        """
        Soft delete: desactiva el usuario en lugar de borrarlo.
        DRF automáticamente retorna 204 NO CONTENT.
        """
        instance.activo = False
        instance.is_active = False
        instance.save()
        logger.info(f"Usuario {instance.username} desactivado por {self.request.user.username}")

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def profile(self, request):
        """
        Endpoint personalizado: GET /api/usuarios/profile/
        Retorna el perfil del usuario autenticado.
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)  # DRF automáticamente usa status 200

    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated])
    def reactivate(self, request, pk=None):
        """
        Endpoint personalizado: PATCH /api/usuarios/{id}/reactivate/
        Reactiva un usuario desactivado.
        Solo accesible por administradores.
        """
        try:
            # Obtener usuario (incluso si está desactivado)
            usuario = Usuario.objects.get(pk=pk)
            
            # Verificar permisos: solo administradores pueden reactivar
            if request.user.rol != 'Administrador':
                logger.warning(
                    f"Usuario {request.user.username} intentó reactivar sin permisos"
                )
                return Response(
                    {'detail': 'Solo los administradores pueden reactivar usuarios'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Verificar si el usuario ya está activo
            if usuario.activo:
                return Response(
                    {'detail': 'El usuario ya está activo'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Reactivar usuario
            usuario.activo = True
            usuario.is_active = True
            usuario.save()
            
            logger.info(
                f"Usuario {usuario.username} reactivado por {request.user.username}"
            )
            
            serializer = self.get_serializer(usuario)
            return Response(serializer.data, status=status.HTTP_200_OK)
            
        except Usuario.DoesNotExist:
            logger.error(f"Intento de reactivar usuario inexistente: {pk}")
            return Response(
                {'detail': 'Usuario no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error al reactivar usuario {pk}: {str(e)}")
            return Response(
                {'detail': f'Error al reactivar usuario: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
