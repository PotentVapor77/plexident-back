from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from api.clinical_records.repositories import ClinicalRecordRepository
from api.clinical_records.services.vital_signs_service import VitalSignsService
from api.clinical_records.services.form033_storage_service import Form033StorageService
from api.clinical_records.serializers import (
    WritableAntecedentesPersonalesSerializer,
    WritableAntecedentesFamiliaresSerializer,
    WritableConstantesVitalesSerializer,
    WritableExamenEstomatognaticoSerializer,
    Form033SnapshotSerializer
)

class PatientDataReloadViewSet(viewsets.ViewSet):
    """
    ViewSet para obtener los datos más recientes de secciones específicas
    útil para recargar formularios en el frontend.
    """

    @action(detail=False, methods=['get'], url_path='antecedentes-personales/(?P<paciente_id>[^/.]+)/latest')
    def antecedentes_personales(self, request, paciente_id=None):
        ultimos_datos = ClinicalRecordRepository.obtener_ultimos_datos_paciente(paciente_id)
        antecedentes = ultimos_datos.get('antecedentes_personales')
        if not antecedentes:
            return Response({'detail': 'No hay antecedentes previos'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = WritableAntecedentesPersonalesSerializer(antecedentes)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='antecedentes-familiares/(?P<paciente_id>[^/.]+)/latest')
    def antecedentes_familiares(self, request, paciente_id=None):
        ultimos_datos = ClinicalRecordRepository.obtener_ultimos_datos_paciente(paciente_id)
        antecedentes = ultimos_datos.get('antecedentes_familiares')
        if not antecedentes:
            return Response({'detail': 'No hay antecedentes previos'}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = WritableAntecedentesFamiliaresSerializer(antecedentes)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='constantes-vitales/(?P<paciente_id>[^/.]+)/latest')
    def constantes_vitales(self, request, paciente_id=None):
        # VitalSignsService ya tiene un método para esto
        ultima_cv = VitalSignsService.obtener_ultima_constante(paciente_id)
        if not ultima_cv:
            return Response({'detail': 'No hay constantes vitales previas'}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = WritableConstantesVitalesSerializer(ultima_cv)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='examen-estomatognatico/(?P<paciente_id>[^/.]+)/latest')
    def examen_estomatognatico(self, request, paciente_id=None):
        ultimos_datos = ClinicalRecordRepository.obtener_ultimos_datos_paciente(paciente_id)
        examen = ultimos_datos.get('examen_estomatognatico')
        if not examen:
            return Response({'detail': 'No hay examen previo'}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = WritableExamenEstomatognaticoSerializer(examen)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='odontograma-2d/(?P<paciente_id>[^/.]+)/latest')
    def odontograma_snapshot(self, request, paciente_id=None):
        """
        Obtiene el último snapshot (Form033) guardado para el paciente.
        """
        # Primero obtenemos el último historial clínico del paciente
        ultimo_historial = ClinicalRecordRepository.obtener_ultimo_historial_por_paciente(paciente_id)
        if not ultimo_historial:
             return Response({'detail': 'No hay historiales previos'}, status=status.HTTP_404_NOT_FOUND)

        # Buscamos el snapshot asociado a ese historial
        snapshot = Form033StorageService.obtener_snapshot_por_historial(ultimo_historial.id)
        if not snapshot:
            return Response({'detail': 'No hay odontograma previo'}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = Form033SnapshotSerializer(snapshot)
        return Response(serializer.data)