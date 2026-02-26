# api/odontogram/views/indicadores_views.py

"""
Vistas para Indicadores de Salud Bucal y Piezas Índice
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q

from api.odontogram.services.piezas_service import PiezasIndiceService
from api.odontogram.models import Paciente, IndicadoresSaludBucal
from api.odontogram.serializers import IndicadoresSaludBucalSerializer  # ajusta la ruta si es distinta


# ============================================================================
# PAGINACIÓN ESTÁNDAR
# ============================================================================

class IndicadoresPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            "success": True,
            "status_code": status.HTTP_200_OK,
            "message": "Indicadores obtenidos correctamente",
            "data": {
                "count": self.page.paginator.count,
                "total_pages": self.page.paginator.num_pages,
                "current_page": self.page.number,
                "page_size": self.get_page_size(self.request),
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
            },
            "errors": None,
        })


# ============================================================================
# ENDPOINTS DE INDICADORES
# ============================================================================

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def listar_indicadores(request):
    """
    GET /api/odontogram/indicadores/
    Lista indicadores con soporte de búsqueda y paginación.

    Query params:
      - paciente   (UUID)   : filtra por paciente
      - search     (str)    : busca en fecha, enf. periodontal, oclusión, fluorosis
      - page       (int)    : número de página
      - page_size  (int)    : tamaño de página (máx 100)
    """
    queryset = IndicadoresSaludBucal.objects.filter(activo=True).select_related("paciente")

    # Filtro por paciente
    paciente_id = request.query_params.get("paciente")
    if paciente_id:
        queryset = queryset.filter(paciente_id=paciente_id)

    # Búsqueda global
    search = request.query_params.get("search", "").strip()
    if search:
        queryset = queryset.filter(
            Q(fecha__icontains=search)
            | Q(enfermedad_periodontal__icontains=search)
            | Q(tipo_oclusion__icontains=search)
            | Q(nivel_fluorosis__icontains=search)
            | Q(paciente__nombres__icontains=search)
            | Q(paciente__apellidos__icontains=search)
            | Q(paciente__cedula_pasaporte__icontains=search)
        )

    queryset = queryset.order_by("-fecha")

    paginator = IndicadoresPagination()
    page = paginator.paginate_queryset(queryset, request)
    if page is not None:
        serializer = IndicadoresSaludBucalSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    serializer = IndicadoresSaludBucalSerializer(queryset, many=True)
    return Response({
        "success": True,
        "status_code": status.HTTP_200_OK,
        "message": "Indicadores obtenidos correctamente",
        "data": serializer.data,
        "errors": None,
    })


class IndicadoresPiezasView:
    """
    Vista de utilidades para manejar información de piezas índice
    """
    
    @staticmethod
    def obtener_informacion_piezas(paciente_id: str) -> Response:
        """
        Obtiene información sobre qué piezas dentales usar para los indicadores,
        incluyendo alternativas si las principales no están disponibles.
        
        Args:
            paciente_id: UUID del paciente
            
        Returns:
            Response con información de piezas disponibles
        """
        try:
            # Verificar que el paciente existe
            paciente = get_object_or_404(Paciente, id=paciente_id)
            
            # Obtener información de piezas
            info_piezas = PiezasIndiceService.obtener_informacion_piezas(paciente_id)
            
            return Response({
                'success': True,
                'status_code': status.HTTP_200_OK,
                'message': 'Información de piezas obtenida correctamente',
                'data': info_piezas,
                'errors': None
            }, status=status.HTTP_200_OK)
            
        except Paciente.DoesNotExist:
            return Response({
                'success': False,
                'status_code': status.HTTP_404_NOT_FOUND,
                'message': f'Paciente con ID {paciente_id} no encontrado',
                'data': None,
                'errors': {'paciente_id': ['Paciente no existe']}
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({
                'success': False,
                'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': f'Error al obtener información de piezas: {str(e)}',
                'data': None,
                'errors': {'detail': [str(e)]}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @staticmethod
    def verificar_disponibilidad(paciente_id: str) -> Response:
        """
        Verifica si hay suficientes piezas dentales disponibles para crear
        indicadores de salud bucal válidos.
        
        Args:
            paciente_id: UUID del paciente
            
        Returns:
            Response con información de disponibilidad
        """
        try:
            # Verificar que el paciente existe
            paciente = get_object_or_404(Paciente, id=paciente_id)
            
            # Obtener información de piezas
            info_piezas = PiezasIndiceService.obtener_informacion_piezas(paciente_id)
            
            # Calcular piezas disponibles (originales + alternativas)
            piezas_disponibles = (
                info_piezas['estadisticas']['piezas_originales'] + 
                info_piezas['estadisticas']['piezas_alternativas']
            )
            
            # Se requieren al menos 3 piezas para cálculos válidos
            puede_crear = piezas_disponibles >= 3
            
            if puede_crear:
                mensaje = f"Puede crear indicadores. {piezas_disponibles} piezas disponibles."
            else:
                mensaje = (
                    f"No hay suficientes piezas dentales disponibles. "
                    f"Se requieren al menos 3 piezas, solo hay {piezas_disponibles} disponibles."
                )
            
            return Response({
                'success': True,
                'status_code': status.HTTP_200_OK,
                'message': 'Verificación completada',
                'data': {
                    'puede_crear_indicadores': puede_crear,
                    'piezas_disponibles': piezas_disponibles,
                    'mensaje': mensaje,
                    'denticion': info_piezas['denticion'],
                    'estadisticas': info_piezas['estadisticas']
                },
                'errors': None
            }, status=status.HTTP_200_OK)
            
        except Paciente.DoesNotExist:
            return Response({
                'success': False,
                'status_code': status.HTTP_404_NOT_FOUND,
                'message': f'Paciente con ID {paciente_id} no encontrado',
                'data': None,
                'errors': {'paciente_id': ['Paciente no existe']}
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({
                'success': False,
                'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'message': f'Error al verificar disponibilidad: {str(e)}',
                'data': None,
                'errors': {'detail': [str(e)]}
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# DECORADORES PARA ENDPOINTS
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def obtener_informacion_piezas_indice(request, paciente_id):
    """
    GET /api/odontogram/indicadores/piezas-indice/{paciente_id}/
    
    Obtiene información sobre qué piezas dentales usar para los indicadores,
    incluyendo alternativas si las principales no están disponibles.
    
    Respuesta:
    {
        "success": true,
        "status_code": 200,
        "message": "Información de piezas obtenida correctamente",
        "data": {
            "denticion": "permanente",
            "piezas": {
                "16": {
                    "codigo_usado": "17",
                    "es_alternativa": true,
                    "disponible": true,
                    "codigo_original": "16",
                    "diente_id": "uuid",
                    "ausente": false
                },
                ...
            },
            "estadisticas": {
                "total_piezas": 6,
                "piezas_originales": 4,
                "piezas_alternativas": 2,
                "piezas_no_disponibles": 0,
                "porcentaje_disponible": 100.0
            }
        },
        "errors": null
    }
    """
    return IndicadoresPiezasView.obtener_informacion_piezas(paciente_id)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verificar_disponibilidad_piezas(request, paciente_id):
    """
    GET /api/odontogram/indicadores/verificar-piezas/{paciente_id}/
    
    """
    return IndicadoresPiezasView.verificar_disponibilidad(paciente_id)