# api/odontogram/views/catalogo_views.py
"""
ViewSets para el catálogo (lectura)
- Categorías de diagnósticos
- Diagnósticos
- Áreas afectadas
- Tipos de atributos clínicos
- Configuración
"""

import logging
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.db.models import Q

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from api.odontogram.models import (
    CategoriaDiagnostico,
    Diagnostico,
    AreaAfectada,
    TipoAtributoClinico,
)

from api.odontogram.serializers import (
    CategoriaDiagnosticoSerializer,
    DiagnosticoListSerializer,
    DiagnosticoDetailSerializer,
    AreaAfectadaSerializer,
    TipoAtributoClinicoSerializer,
    OdontogramaConfigSerializer,
)

from api.odontogram.repositories.odontogram_repositories import (
    CategoriaDiagnosticoRepository,
    DiagnosticoRepository,
    AreaAfectadaRepository,
    TipoAtributoClinicoRepository,
)

from api.odontogram.services.odontogram_services import OdontogramaService

logger = logging.getLogger(__name__)


# ==================== CATÁLOGO VIEWSETS ====================


class CategoriaDiagnosticoViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para categorías de diagnóstico (catálogo)"""
    
    serializer_class = CategoriaDiagnosticoSerializer
    permission_classes = [IsAuthenticated]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.repository = CategoriaDiagnosticoRepository()
    
    def get_queryset(self):
        return self.repository.get_with_diagnosticos()
    
    @action(detail=False, methods=['get'])
    def por_prioridad(self, request):
        """GET /api/catalogo/categorias/por_prioridad/?prioridad=ALTA"""
        prioridad_key = request.query_params.get('prioridad')
        
        if not prioridad_key:
            return Response(
                {'error': 'Se requiere el parámetro prioridad'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        categorias = self.repository.get_by_prioridad(prioridad_key)
        serializer = self.get_serializer(categorias, many=True)
        return Response(serializer.data)


class DiagnosticoViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para diagnósticos del catálogo"""
    
    permission_classes = [IsAuthenticated]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.repository = DiagnosticoRepository()
    
    def get_queryset(self):
        return self.repository.get_all().select_related('categoria')
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return DiagnosticoDetailSerializer
        return DiagnosticoListSerializer
    
    def retrieve(self, request, pk=None):
        """GET /api/catalogo/diagnosticos/{id}/ con caché"""
        cache_key = f'odontograma:diagnostico:{pk}'
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return Response(cached_data)
        
        diagnostico_data = self.repository.get_by_id(int(pk))
        
        if not diagnostico_data:
            return Response(
                {'error': 'Diagnóstico no encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(diagnostico_data)
        cache.set(cache_key, serializer.data, timeout=3600)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def por_categoria(self, request):
        """GET /api/catalogo/diagnosticos/por_categoria/?categoria_id=1"""
        categoria_id = request.query_params.get('categoria_id')
        
        if not categoria_id:
            return Response(
                {'error': 'Se requiere el parámetro categoria_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        diagnosticos = self.repository.get_by_categoria(int(categoria_id))
        serializer = self.get_serializer(diagnosticos, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def criticos(self, request):
        """GET /api/catalogo/diagnosticos/criticos/"""
        diagnosticos = self.repository.get_criticos()
        serializer = self.get_serializer(diagnosticos, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def buscar(self, request):
        """GET /api/catalogo/diagnosticos/buscar/?q=caries"""
        query = request.query_params.get('q')
        
        if not query:
            return Response(
                {'error': 'Se requiere el parámetro q'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        diagnosticos = self.repository.search(query)
        serializer = self.get_serializer(diagnosticos, many=True)
        return Response(serializer.data)


class AreaAfectadaViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para áreas afectadas"""
    
    serializer_class = AreaAfectadaSerializer
    permission_classes = [IsAuthenticated]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.repository = AreaAfectadaRepository()
    
    def get_queryset(self):
        return self.repository.get_all()


class TipoAtributoClinicoViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para tipos de atributos clínicos"""
    
    serializer_class = TipoAtributoClinicoSerializer
    permission_classes = [IsAuthenticated]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.repository = TipoAtributoClinicoRepository()
    
    def get_queryset(self):
        return self.repository.get_with_opciones()


class OdontogramaConfigViewSet(viewsets.ViewSet):
    """ViewSet para obtener configuración completa del odontograma"""
    
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def config(self, request):
        """GET /api/catalogo/config/ - Configuración completa con caché"""
        cache_key = 'odontograma:config:full'
        cached_config = cache.get(cache_key)
        
        if cached_config:
            return Response(cached_config)
        
        service = OdontogramaService()
        config = service.get_full_config()
        
        serializer = OdontogramaConfigSerializer(config)
        cache.set(cache_key, serializer.data, timeout=3600)
        return Response(serializer.data)