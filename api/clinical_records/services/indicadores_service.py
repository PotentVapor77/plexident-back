from venv import logger
from api.odontogram.models import IndicadoresSaludBucal
from api.clinical_records.models.clinical_record import ClinicalRecord


class ClinicalRecordIndicadoresService:
    @staticmethod
    def obtener_indicadores_paciente(paciente_id): # <-- Nombre exacto
        try:
            return IndicadoresSaludBucal.objects.filter(
                paciente_id=paciente_id,
                activo=True
            ).order_by('-fecha').first()
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return None

    @staticmethod
    def refrescar_en_historial(historial_id: str):
        """
        Fuerza la actualización de la referencia de indicadores 
        en el texto de observaciones o logs del historial si es necesario.
        """
        try:
            historial = ClinicalRecord.objects.get(id=historial_id)
            indicadores = ClinicalRecordIndicadoresService.obtener_indicadores_actuales(historial.paciente_id)
            
            if indicadores:
                return indicadores
            return None
        except ClinicalRecord.DoesNotExist:
            return None