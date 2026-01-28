"""
ViewSet para gestión de odontogramas
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .base import (
    ClinicalRecordPagination,
    BasePermissionMixin,
    QuerysetOptimizationMixin,
    LoggingMixin,
    logger,
)

# TODO: Importar modelo y serializers cuando estén disponibles
# from api.clinical_records.models import Odontogram
# from api.clinical_records.serializers import OdontogramSerializer


class OdontogramViewSet(
    BasePermissionMixin,
    QuerysetOptimizationMixin,
    LoggingMixin,
    viewsets.ModelViewSet,
):
    """
    ViewSet para gestión de odontogramas
    
    Endpoints futuros:
        - GET    /api/odontograms/                      - Listar odontogramas
        - GET    /api/odontograms/{id}/                 - Detalle de odontograma
        - GET    /api/odontograms/by-clinical-record/   - Por historial clínico
        - POST   /api/odontograms/                      - Crear odontograma
        - PATCH  /api/odontograms/{id}/                 - Actualizar odontograma
        - POST   /api/odontograms/{id}/actualizar-diente/ - Actualizar diente específico
    """
    
    # queryset = Odontogram.objects.all()
    permission_model_name = 'odontograma'
    pagination_class = ClinicalRecordPagination
    
    # TODO: Implementar cuando el modelo esté listo
    
    @action(detail=True, methods=['post'], url_path='actualizar-diente')
    def actualizar_diente(self, request, pk=None):
        """
        Actualizar el estado de un diente específico en el odontograma
        
        POST: /api/odontograms/{id}/actualizar-diente/
        Body: {
            "numero_diente": 18,
            "estado": "CARIES",
            "observaciones": "Caries profunda"
        }
        """
        # TODO: Implementar lógica
        return Response(
            {'detail': 'Endpoint pendiente de implementación'},
            status=status.HTTP_501_NOT_IMPLEMENTED
        )
    
    @action(detail=False, methods=['get'], url_path='by-clinical-record')
    def by_clinical_record(self, request):
        """
        Obtener odontograma de un historial clínico específico
        
        GET: /api/odontograms/by-clinical-record/?clinical_record_id={uuid}
        """
        # TODO: Implementar lógica
        return Response(
            {'detail': 'Endpoint pendiente de implementación'},
            status=status.HTTP_501_NOT_IMPLEMENTED
        )
        
    
