# api/clinical_records/views/oral_health_indicators_viewset.py
"""
ViewSet para gestión de indicadores de salud bucal dentro del historial clínico

FIX BRECHA 3: Eliminados endpoints duplicados con ClinicalRecordViewSet.
    - latest_indicadores_salud_bucal → ELIMINADO (duplicado de ClinicalRecordViewSet.latest_indicadores_salud)
    - obtener_indicadores_historial → ELIMINADO (duplicado de ClinicalRecordViewSet.obtener_indicadores_historial)
    
Este ViewSet conserva solo los endpoints ÚNICOS:
    - recargar (con contexto de suplentes y advertencias)
    - historial por ID
    - validar piezas
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
    #BasePermissionMixin,
    QuerysetOptimizationMixin,
    LoggingMixin,
    viewsets.ViewSet
):
    """
    ViewSet para indicadores de salud bucal en contexto de historial clínico
    
    Endpoints ÚNICOS (no duplicados con ClinicalRecordViewSet):
        - GET  /api/clinical-records/indicadores-salud-bucal/{paciente_id}/recargar/
        - GET  /api/clinical-records/indicadores-salud-bucal/historial/{historial_id}/
        - GET  /api/clinical-records/validar-piezas-indicadores/{paciente_id}/
    
    Endpoints DELEGADOS a ClinicalRecordViewSet:
        - GET  /api/clinical-records/indicadores-salud-bucal/{paciente_id}/latest/
        - GET  /api/clinical-records/{id}/indicadores-salud-bucal/
    """
    
    permission_model_name = 'indicadores_salud_bucal'
    pagination_class = ClinicalRecordPagination

    # ===== FIX BRECHA 3: Endpoint latest ELIMINADO =====
    # Era duplicado exacto de ClinicalRecordViewSet.latest_indicadores_salud
    # URL canónica: GET /api/clinical-records/indicadores-salud-bucal/{paciente_id}/latest/
    # ===================================================

    @action(detail=False, methods=['get'], url_path=r'indicadores-salud-bucal/(?P<paciente_id>[^/]+)/recargar')
    def recargar_indicadores_salud_bucal(self, request, paciente_id=None):
        """
        Recarga los últimos indicadores de salud bucal para prellenar formulario
        CON contexto de piezas suplentes y advertencias de cambios.
        
        GET: /api/clinical-records/indicadores-salud-bucal/{paciente_id}/recargar/
        
        Este endpoint es ÚNICO porque agrega lógica de comparación
        entre piezas del registro anterior vs estado actual.
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

    # ===== FIX BRECHA 3: Endpoint obtener_indicadores_historial ELIMINADO =====
    # Era duplicado exacto de ClinicalRecordViewSet.obtener_indicadores_historial
    # URL canónica: GET /api/clinical-records/{id}/indicadores-salud-bucal/
    # ===========================================================================

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
            
            return Response(data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error obteniendo indicadores para historial {historial_id}: {str(e)}")
            return Response(
                {'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
    def _validar_puede_recargar(self, paciente_id):
        """
        Valida que el paciente existe y tiene permisos
        
        Returns:
            tuple: (historial, error_message)
        """
        try:
            from api.patients.models.paciente import Paciente
            
            # Verificar que el paciente existe
            paciente = Paciente.objects.filter(id=paciente_id, activo=True).first()
            if not paciente:
                return None, 'Paciente no encontrado o inactivo'
            
            return paciente, None
            
        except Exception as e:
            logger.error(f"Error validando recarga: {str(e)}")
            return None, f'Error de validación: {str(e)}'
        
        
    @action(
        detail=False, 
        methods=['get'], 
        url_path=r'validar-piezas-indicadores/(?P<paciente_id>[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})'
    )
    def validar_piezas_indicadores(self, request, paciente_id=None):
        """
        Valida disponibilidad de piezas antes de crear/editar indicadores.
        
        FIX BRECHA 2: Ahora incluye flag 'ambos_ausentes' para piezas
        donde ni la original ni la suplente están disponibles.
        """
        from api.odontogram.services.piezas_service import PiezasIndiceService
        
        info_piezas = PiezasIndiceService.obtener_informacion_piezas(str(paciente_id))
        
        # FIX BRECHA 2: Generar advertencias detalladas incluyendo "ambos ausentes"
        advertencias = []
        piezas_sin_disponibilidad = []
        
        for codigo, info in info_piezas['piezas_mapeo'].items():
            if info.get('ambos_ausentes', False):
                advertencias.append({
                    'tipo': 'ambos_ausentes',
                    'pieza': codigo,
                    'mensaje': f"Pieza {codigo} y su suplente no están disponibles. "
                              f"No se podrá registrar esta posición."
                })
                piezas_sin_disponibilidad.append(codigo)
            elif info.get('es_alternativa', False):
                advertencias.append({
                    'tipo': 'suplente',
                    'pieza': codigo,
                    'mensaje': f"Se usará pieza {info['codigo_usado']} como suplente de {codigo}"
                })
        
        return Response({
            'puede_crear_indicadores': info_piezas['estadisticas']['total_piezas'] >= 3,
            'piezas_disponibles': info_piezas['estadisticas']['total_piezas'],
            'piezas_originales': info_piezas['estadisticas']['piezas_originales'],
            'piezas_suplentes': info_piezas['estadisticas']['piezas_alternativas'],
            'piezas_sin_disponibilidad': piezas_sin_disponibilidad,
            'detalle_piezas': info_piezas['piezas_mapeo'],
            'advertencias': advertencias
        })