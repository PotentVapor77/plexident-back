# odontogram/views.py

"""Vistas para la API REST del sistema de odontogramas extensible."""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Prefetch

from .models import (
    CategoriaDiagnostico,
    Diagnostico,
    AreaAfectada,
    TipoAtributoClinico,
    OpcionAtributoClinico,
)
from .serializers import (
    CategoriaDiagnosticoSerializer,
    DiagnosticoListSerializer,
    DiagnosticoDetailSerializer,
    AreaAfectadaSerializer,
    TipoAtributoClinicoSerializer,
    OdontogramaConfigSerializer,
)


class CategoriaDiagnosticoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para gestionar categorías de diagnóstico
    GET /api/categorias/ - Lista todas las categorías
    GET /api/categorias/{id}/ - Detalle de una categoría
    """
    queryset = CategoriaDiagnostico.objects.filter(activo=True).prefetch_related('diagnosticos')
    serializer_class = CategoriaDiagnosticoSerializer


class DiagnosticoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para gestionar diagnósticos
    GET /api/diagnosticos/ - Lista todos los diagnósticos
    GET /api/diagnosticos/{id}/ - Detalle completo de un diagnóstico
    """
    queryset = Diagnostico.objects.filter(activo=True).select_related('categoria')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return DiagnosticoDetailSerializer
        return DiagnosticoListSerializer

    @action(detail=False, methods=['get'])
    def por_categoria(self, request):
        """
        GET /api/diagnosticos/por_categoria/?categoria_id=1
        Filtra diagnósticos por categoría
        """
        categoria_id = request.query_params.get('categoria_id')
        if not categoria_id:
            return Response(
                {'error': 'Se requiere el parámetro categoria_id'},
                status=status.HTTP_400_BAD_REQUEST
            )

        diagnosticos = self.get_queryset().filter(categoria_id=categoria_id)
        serializer = self.get_serializer(diagnosticos, many=True)
        return Response(serializer.data)


class AreaAfectadaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para gestionar áreas afectadas
    """
    queryset = AreaAfectada.objects.filter(activo=True)
    serializer_class = AreaAfectadaSerializer


class TipoAtributoClinicoViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para gestionar tipos de atributos clínicos
    """
    queryset = TipoAtributoClinico.objects.filter(activo=True).prefetch_related(
        Prefetch(
            'opciones',
            queryset=OpcionAtributoClinico.objects.filter(activo=True).order_by('orden')
        )
    )
    serializer_class = TipoAtributoClinicoSerializer


class OdontogramaConfigViewSet(viewsets.ViewSet):
    """
    ViewSet especial que retorna toda la configuración del odontograma
    GET /api/odontograma/config/ - Configuración completa
    """

    @action(detail=False, methods=['get'])
    def config(self, request):
        """
        Retorna toda la configuración necesaria para el frontend
        """
        data = {
            'categorias': CategoriaDiagnostico.objects.filter(
                activo=True
            ).prefetch_related('diagnosticos'),
            'areas_afectadas': AreaAfectada.objects.filter(activo=True),
            'tipos_atributos': TipoAtributoClinico.objects.filter(
                activo=True
            ).prefetch_related(
                Prefetch(
                    'opciones',
                    queryset=OpcionAtributoClinico.objects.filter(activo=True).order_by('orden')
                )
            ),
        }

        serializer = OdontogramaConfigSerializer(data)
        return Response(serializer.data)
