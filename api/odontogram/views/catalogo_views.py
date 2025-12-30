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
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError

from api.odontogram.models import (
    CategoriaDiagnostico,
    Diagnostico,
    AreaAfectada,
    SuperficieDental,
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

    # AGREGAR ESTE MÉTODO
    @action(detail=False, methods=['get'], url_path='con-diagnosticos')
    def con_diagnosticos(self, request):
        """
        GET /api/odontogram/catalogo/categorias/con-diagnosticos/
        Retorna todas las categorías activas con sus diagnósticos anidados
        """
        # Usar caché para mejorar rendimiento
        cache_key = "odontograma:categorias:con_diagnosticos"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            logger.info("Retornando categorías desde caché")
            return Response(cached_data, status=status.HTTP_200_OK)
        
        # Obtener categorías con diagnósticos desde el repository
        categorias = self.repository.get_with_diagnosticos()
        
        # Serializar con diagnósticos anidados
        data = []
        for categoria in categorias:
            categoria_data = CategoriaDiagnosticoSerializer(categoria).data
            
            # Agregar diagnósticos activos de esta categoría
            diagnosticos_activos = categoria.diagnosticos.filter(activo=True)
            categoria_data['diagnosticos'] = DiagnosticoListSerializer(
                diagnosticos_activos,
                many=True
            ).data
            
            data.append(categoria_data)
        
        # Cachear por 1 hora
        cache.set(cache_key, data, timeout=3600)
        
        logger.info(f"Retornando {len(data)} categorías con diagnósticos")
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def por_prioridad(self, request):
        """GET /api/odontogram/catalogo/categorias/por_prioridad/?prioridad=ALTA"""
        prioridad_key = request.query_params.get("prioridad")
        if not prioridad_key:
            raise ValidationError({"prioridad": ["Se requiere el parámetro prioridad"]})
        
        categorias = self.repository.get_by_prioridad(prioridad_key)
        serializer = self.get_serializer(categorias, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def filtrar_por_superficie(self, request):
        """
        Filtra diagnósticos aplicables según superficie del frontend
        GET /api/odontogram/catalogo/categorias/filtrar_por_superficie/?superficie_id={id_frontend}
        """
        superficie_id = request.query_params.get("superficie_id")
        if not superficie_id:
            raise ValidationError(
                {"superficie_id": ["Parámetro superficie_id requerido"]}
            )
        
        # Obtener área anatómica desde el ID del frontend
        area = SuperficieDental.obtener_area_desde_frontend(superficie_id)
        
        # Filtrar diagnósticos aplicables a esa área
        diagnosticos = (
            Diagnostico.objects.filter(
                activo=True,
                areas_relacionadas__area__key=area,
            )
            .distinct()
            .select_related("categoria")
        )
        
        diagnosticos_serializer = DiagnosticoListSerializer(diagnosticos, many=True)
        return Response(
            {
                "superficie_id_frontend": superficie_id,
                "area_anatomica": area,
                "diagnosticos": diagnosticos_serializer.data,
            },
            status=status.HTTP_200_OK,
        )


class DiagnosticoViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet para diagnósticos del catálogo"""

    permission_classes = [IsAuthenticated]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.repository = DiagnosticoRepository()

    def get_queryset(self):
        return self.repository.get_all().select_related("categoria")

    def get_serializer_class(self):
        if self.action == "retrieve":
            return DiagnosticoDetailSerializer
        return DiagnosticoListSerializer

    def retrieve(self, request, pk=None):
        """GET /api/odontogram/catalogo/diagnosticos/{id}/ con caché"""
        cache_key = f"odontograma:diagnostico:{pk}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)

        diagnostico_data = self.repository.get_by_id(int(pk))
        if not diagnostico_data:
            raise ValidationError({"detail": ["Diagnóstico no encontrado"]})

        serializer = self.get_serializer(diagnostico_data)
        cache.set(cache_key, serializer.data, timeout=3600)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def por_categoria(self, request):
        """GET /api/odontogram/catalogo/diagnosticos/por_categoria/?categoria_id=1"""
        categoria_id = request.query_params.get("categoria_id")
        if not categoria_id:
            raise ValidationError(
                {"categoria_id": ["Se requiere el parámetro categoria_id"]}
            )

        diagnosticos = self.repository.get_by_categoria(int(categoria_id))
        serializer = self.get_serializer(diagnosticos, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def criticos(self, request):
        """GET /api/odontogram/catalogo/diagnosticos/criticos/"""
        diagnosticos = self.repository.get_criticos()
        serializer = self.get_serializer(diagnosticos, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def buscar(self, request):
        """GET /api/odontogram/catalogo/diagnosticos/buscar/?q=caries"""
        query = request.query_params.get("q")
        if not query:
            raise ValidationError({"q": ["Se requiere el parámetro q"]})

        diagnosticos = self.repository.search(query)
        serializer = self.get_serializer(diagnosticos, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


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

    @action(detail=False, methods=["get"])
    def config(self, request):
        """GET /api/odontogram/catalogo/config/ - Configuración completa con caché"""
        cache_key = "odontograma:config:full"
        cached_config = cache.get(cache_key)
        if cached_config:
            return Response(cached_config, status=status.HTTP_200_OK)

        service = OdontogramaService()
        config = service.get_full_config()
        serializer = OdontogramaConfigSerializer(config)

        cache.set(cache_key, serializer.data, timeout=3600)
        return Response(serializer.data, status=status.HTTP_200_OK)
