# api/users/views.py

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound

from api.users.permissions import UserBasedPermission
from .models import PermisoUsuario, Usuario
from .serializers import (
    PermisoUsuarioCreateUpdateSerializer,
    PermisoUsuarioSerializer,
    UsuarioSerializer,
    UsuarioCreateSerializer,
    UsuarioUpdateSerializer
)

import logging
logger = logging.getLogger(__name__)


class UsuarioPagination(PageNumberPagination):
    """Configuración de paginación para usuarios"""
    page_size = 10  # Cambiado a 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class UsuarioViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de usuarios"""
    serializer_class = UsuarioSerializer
    queryset = Usuario.objects.all()
    permission_classes = [IsAuthenticated, UserBasedPermission]
    permission_model_name = "usuario"
    pagination_class = UsuarioPagination

    def get_queryset(self):
        """Queryset base con filtros y búsqueda"""
        request = self.request
        search = (request.query_params.get("search") or "").strip()
        is_active_param = request.query_params.get("is_active")
        
        qs = Usuario.objects.select_related(
            "creado_por",
            "actualizado_por",
        ).order_by("-fecha_creacion")
        
        # Filtrar por estado
        if is_active_param is not None:
            is_active = is_active_param.lower() == 'true'
            qs = qs.filter(is_active=is_active)
        
        # Búsqueda
        if search:
            qs = qs.filter(
                Q(username__icontains=search)
                | Q(nombres__icontains=search)
                | Q(apellidos__icontains=search)
                | Q(correo__icontains=search)
            )
        
        return qs

    def get_serializer_class(self):
        """Retorna el serializer apropiado según la acción"""
        if self.action == 'create':
            return UsuarioCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UsuarioUpdateSerializer
        return UsuarioSerializer

    def perform_destroy(self, instance):
        """Soft delete: desactiva el usuario"""
        instance.is_active = False
        instance.save()
        logger.info(f"Usuario {instance.username} desactivado por {self.request.user.username}")

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def profile(self, request):
        """GET /api/usuarios/profile/ - Perfil del usuario autenticado"""
        serializer = self.get_serializer(request.user)
        #  El renderer formatea automáticamente
        return Response(serializer.data)


class PermisoUsuarioViewSet(viewsets.ModelViewSet):
    """
    ViewSet para permisos por usuario individual.
     EXCLUYE ADMINISTRADORES
    """
    queryset = PermisoUsuario.objects.filter(
        usuario__rol__in=['Odontologo', 'Asistente']
    ).select_related('usuario').order_by("usuario__username", "modelo")
    
    serializer_class = PermisoUsuarioSerializer
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PermisoUsuarioCreateUpdateSerializer
        return PermisoUsuarioSerializer

    @action(detail=False, methods=["get"], url_path="by_user")
    def by_user(self, request):
        """GET /api/permisos-usuario/by_user/?user_id=UUID"""
        user_id = request.query_params.get("user_id")
        
        #  Validar parámetro requerido
        if not user_id:
            raise ValidationError({'user_id': 'Este parámetro es requerido'})
        
        #  Usar get_object_or_404
        usuario = get_object_or_404(Usuario, id=user_id)
        
        #  Validar rol
        if usuario.rol == 'Administrador':
            raise PermissionDenied("No se pueden consultar permisos de administradores")
        
        # Obtener o crear permisos
        permisos = PermisoUsuario.objects.filter(usuario=usuario).order_by("modelo")
        
        if not permisos.exists():
            modelos = ['usuario', 'paciente', 'agenda', 'odontograma', 'historia_clinica', 'clinical_files']
            for modelo in modelos:
                PermisoUsuario.objects.create(
                    usuario=usuario,
                    modelo=modelo,
                    metodos_permitidos=[]
                )
            permisos = PermisoUsuario.objects.filter(usuario=usuario).order_by("modelo")
        
        serializer = self.get_serializer(permisos, many=True)
        #  Respuesta simple - el renderer se encarga del formato
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="bulk_update")
    def bulk_update(self, request):
        """
        POST /api/permisos-usuario/bulk_update/
        {
            "user_id": "uuid",
            "permisos": [{"modelo": "usuario", "metodos_permitidos": ["GET"]}]
        }
        """
        user_id = request.data.get("user_id")
        data = request.data.get("permisos", [])
        
        # Validaciones
        if not user_id:
            raise ValidationError({'user_id': 'Este campo es requerido'})
        
        if not isinstance(data, list):
            raise ValidationError({'permisos': 'Debe ser una lista'})
        
        #  Obtener usuario
        usuario = get_object_or_404(Usuario, id=user_id)
        
        #  Validar rol
        if usuario.rol == 'Administrador':
            raise PermissionDenied("No se pueden asignar permisos a administradores")
        
        # Actualizar permisos
        actualizados = []
        for permiso_data in data:
            modelo = permiso_data.get("modelo")
            metodos = permiso_data.get("metodos_permitidos", [])
            
            if not modelo:
                continue
            
            # Si está vacío, eliminar
            if not metodos:
                PermisoUsuario.objects.filter(usuario=usuario, modelo=modelo).delete()
                continue
            
            # Actualizar o crear
            permiso, created = PermisoUsuario.objects.update_or_create(
                usuario=usuario,
                modelo=modelo,
                defaults={"metodos_permitidos": metodos},
            )
            actualizados.append(permiso)
        
        logger.info(f"{len(actualizados)} permisos actualizados para {usuario.username}")
        
        serializer = self.get_serializer(actualizados, many=True)
        #  Respuesta simple
        return Response(serializer.data)

    @action(detail=False, methods=["delete"], url_path="delete_by_user")
    def delete_by_user(self, request):
        """DELETE /api/permisos-usuario/delete_by_user/?user_id=UUID&modelo=opcional"""
        user_id = request.query_params.get("user_id")
        modelo = request.query_params.get("modelo")
        
        #  Validar parámetro
        if not user_id:
            raise ValidationError({'user_id': 'Este parámetro es requerido'})
        
        # Obtener usuario
        usuario = get_object_or_404(Usuario, id=user_id)
        
        #  Validar rol
        if usuario.rol == 'Administrador':
            raise PermissionDenied("No se pueden modificar permisos de administradores")
        
        # Eliminar permisos
        if modelo:
            deleted_count, _ = PermisoUsuario.objects.filter(
                usuario=usuario, modelo=modelo
            ).delete()
        else:
            deleted_count, _ = PermisoUsuario.objects.filter(usuario=usuario).delete()
        
        logger.info(f"{deleted_count} permisos eliminados para {usuario.username}")
        
        #  Respuesta simple
        return Response({'deleted_count': deleted_count})
