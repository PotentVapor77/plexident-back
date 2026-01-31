# api/clinical_records/services/indices_caries_service.py
"""
Servicio para obtener los últimos índices CPO/ceo de un paciente
"""

import logging
from typing import Optional
from api.odontogram.services.indice_caries_service import IndiceCariesService as OdontogramIndiceService

from api.clinical_records.serializers.indices_caries_serializers import WritableIndicesCariesSerializer
from api.odontogram.models import IndiceCariesSnapshot

logger = logging.getLogger(__name__)


class ClinicalRecordIndicesCariesService:
    """
    Servicio para manejar índices de caries en contexto de historial clínico
    """
    
    @staticmethod
    def obtener_ultimos_indices(paciente_id: str) -> Optional[IndiceCariesSnapshot]:
        try:
            return IndiceCariesSnapshot.objects.filter(
                paciente_id=paciente_id
            ).order_by('-fecha').first()
        except Exception as e:
            logger.error(f"Error obteniendo últimos índices para paciente {paciente_id}: {str(e)}")
            return None
    
    @staticmethod
    def crear_indices_desde_odontograma(paciente_id: str, usuario_id: int) -> Optional[IndiceCariesSnapshot]:
        """
        Crea nuevos índices de caries a partir del odontograma actual
        """
        try:
            # Obtener índices calculados desde el odontograma
            indices_data = OdontogramIndiceService.calcular_indices_paciente(paciente_id)
            
            if not indices_data:
                logger.warning(f"No se pudieron calcular índices para paciente {paciente_id}")
                return None
            
            perm = indices_data['permanente']
            temp = indices_data['temporal']

            indices = IndiceCariesSnapshot.objects.create(
                paciente_id=paciente_id,
                cpo_c=perm['C'],      
                cpo_p=perm['P'],
                cpo_o=perm['O'],
                cpo_total=perm['total'],
                ceo_c=temp['c'],
                ceo_e=temp['e'],
                ceo_o=temp['o'],
                ceo_total=temp['total']
            )
            
            logger.info(f"Índices de caries creados para paciente {paciente_id}: CPO={indices.cpo_total}")
            
            return indices
            
        except Exception as e:
            logger.error(f"Error creando índices desde odontograma: {str(e)}")
            return None
    
    @staticmethod
    def recargar_ultimos_indices(paciente_id: str) -> dict:
        """
        Recarga los últimos índices de caries para precarga en formulario
        """
        indices = ClinicalRecordIndicesCariesService.obtener_ultimos_indices(paciente_id)
        
        if not indices:
            # Intentar calcular desde odontograma
            indices = ClinicalRecordIndicesCariesService.crear_indices_desde_odontograma(
                paciente_id, 
                usuario_id=None 
            )
        
        if indices:
            
            serializer = WritableIndicesCariesSerializer(indices)
            return {
                'indices_caries': indices,
                'indices_caries_data': serializer.data,
                'disponible': True,
                'origen': 'registro_existente' if indices.pk else 'calculado_odontograma'
            }
        
        return {
            'indices_caries': None,
            'indices_caries_data': None,
            'disponible': False,
            'origen': 'no_disponible'
        }