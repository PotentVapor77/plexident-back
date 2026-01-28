"""
ViewSet para indicadores de salud bucal e índices CPO
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .base import (
    ClinicalRecordPagination,
    BasePermissionMixin,
    LoggingMixin,
)


class OralHealthIndicatorsViewSet(
    BasePermissionMixin,
    LoggingMixin,
    viewsets.ModelViewSet,
):
    """
    ViewSet para gestión de indicadores de salud bucal
    
    Endpoints futuros:
        - GET    /api/oral-health-indicators/           - Listar indicadores
        - GET    /api/oral-health-indicators/{id}/      - Detalle
        - POST   /api/oral-health-indicators/           - Crear indicadores
        - GET    /api/oral-health-indicators/calcular-cpo/ - Calcular índice CPO
    """
    
    permission_model_name = 'indicadores_salud_bucal'
    pagination_class = ClinicalRecordPagination
    
    @action(detail=False, methods=['post'], url_path='calcular-cpo')
    def calcular_cpo(self, request):
        """
        Calcular índices CPO (Cariados, Perdidos, Obturados)
        
        POST: /api/oral-health-indicators/calcular-cpo/
        Body: {
            "clinical_record_id": "uuid",
            "dientes_data": [...]
        }
        """
        # TODO: Implementar cálculo de CPO
        return Response(
            {'detail': 'Endpoint pendiente de implementación'},
            status=status.HTTP_501_NOT_IMPLEMENTED
        )
