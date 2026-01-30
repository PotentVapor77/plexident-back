# api/clinical_records/views/oral_health_indicators_viewset.py
"""
ViewSet para gestión de indicadores de salud bucal dentro del historial clínico
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError

from api.clinical_records.serializers.oral_health_indicators import (
    OralHealthIndicatorsSerializer,
    OralHealthIndicatorsRefreshSerializer
)
from api.clinical_records.services.indicadores_service import ClinicalRecordIndicadoresService
from api.clinical_records.services.clinical_record_service import ClinicalRecordService

from .base import (
    ClinicalRecordPagination,
    BasePermissionMixin,
    QuerysetOptimizationMixin,
    LoggingMixin,
    logger,
)


class OralHealthIndicatorsViewSet(
    BasePermissionMixin,
    QuerysetOptimizationMixin,
    LoggingMixin,
    viewsets.ViewSet
):
    """
    ViewSet para indicadores de salud bucal en contexto de historial clínico
    
    Endpoints:
        - GET    /api/clinical-records/indicadores-salud-bucal/latest/{paciente_id}/ - Últimos indicadores
        - GET    /api/clinical-records/indicadores-salud-bucal/recargar/{paciente_id}/ - Recargar indicadores
        - GET    /api/clinical-records/indicadores-salud-bucal/historial/{historial_id}/ - Indicadores por historial
    """
    
    permission_model_name = 'indicadores_salud_bucal'
    pagination_class = ClinicalRecordPagination
    
    @action(detail=False, methods=['get'], url_path=r'indicadores-salud-bucal/(?P<paciente_id>[^/]+)/latest')
    def latest_indicadores_salud_bucal(self, request, paciente_id=None):
        """
        Obtiene los últimos indicadores de salud bucal de un paciente
        
        GET: /api/clinical-records/indicadores-salud-bucal/{paciente_id}/latest/
        """
        historial, error = self._validar_puede_recargar(paciente_id)
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)

        indicadores = ClinicalRecordIndicadoresService.obtener_indicadores_paciente(paciente_id)
        if not indicadores:
            return Response({'detail': 'No hay indicadores previos'}, status=404)
        
        return Response(OralHealthIndicatorsSerializer(indicadores).data)

    @action(detail=False, methods=['get'], url_path=r'indicadores-salud-bucal/(?P<paciente_id>[^/]+)/recargar')
    def recargar_indicadores_salud_bucal(self, request, paciente_id=None):
        """
        Recarga los últimos indicadores de salud bucal para prellenar formulario
        
        GET: /api/clinical-records/indicadores-salud-bucal/{paciente_id}/recargar/
        """
        historial, error = self._validar_puede_recargar(paciente_id)
        if error:
            return Response({'detail': error}, status=status.HTTP_400_BAD_REQUEST)

        try:
            data = ClinicalRecordIndicadoresService.recargar_indicadores_paciente(paciente_id)
            
            if not data:
                return Response(
                    {'detail': 'No hay indicadores previos para recargar'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            logger.info(f"Indicadores recargados para paciente {paciente_id}")
            return Response(data, status=status.HTTP_200_OK)
            
        except ValidationError as e:
            logger.warning(f"Error recargando indicadores: {str(e)}")
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error recargando indicadores: {str(e)}")
            return Response(
                {'detail': f'Error interno: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'], url_path='indicadores-salud-bucal')
    def obtener_indicadores_historial(self, request, pk=None):
        """
        Obtiene los indicadores de salud bucal asociados a este historial
        
        GET: /api/clinical-records/{id}/indicadores-salud-bucal/
        """
        historial = self.get_object()
        
        indicadores = ClinicalRecordIndicadoresService.obtener_indicadores_paciente(
            str(historial.paciente_id)
        )
        
        if not indicadores:
            return Response(
                {'detail': 'Este historial no tiene indicadores de salud bucal asociados'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        return Response(OralHealthIndicatorsSerializer(indicadores).data)
    
    @action(detail=False, methods=['get'], url_path=r'historial/(?P<historial_id>[^/.]+)')
    def indicadores_por_historial(self, request, historial_id=None):
        """
        Obtiene indicadores asociados a un historial clínico específico
        
        GET: /api/clinical-records/indicadores-salud-bucal/historial/{historial_id}/
        """
        try:
            data = ClinicalRecordService.obtener_indicadores_historial(historial_id)
            
            if not data:
                return Response(
                    {'detail': 'Este historial no tiene indicadores de salud bucal asociados'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            logger.info(f"Indicadores obtenidos para historial {historial_id}")
            
            return Response(data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error obteniendo indicadores para historial {historial_id}: {str(e)}")
            return Response(
                {'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )