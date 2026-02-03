# src/api/clinical_records/services/vital_signs_service.py 

"""
Servicio para manejo de constantes vitales
"""
import logging
from django.utils import timezone
from api.patients.models.constantes_vitales import ConstantesVitales

logger = logging.getLogger(__name__)


class VitalSignsService:
    """Servicio para gestión de constantes vitales"""
    
    # Campos de constantes vitales
    VITAL_FIELDS = ['temperatura', 'pulso', 'frecuencia_respiratoria', 'presion_arterial']
    TEXT_FIELDS = ['motivo_consulta', 'enfermedad_actual']
    
    @classmethod
    def crear_constantes_vitales(cls, paciente, data, creado_por=None):
        """
        Crea nuevas constantes vitales
        
        Args:
            paciente: Instancia del paciente
            data: Diccionario con datos de constantes vitales
            creado_por: Usuario que crea el registro
            
        Returns:
            Instancia de ConstantesVitales creada
        """
        constante_vital_data = {
            'paciente': paciente,
            'temperatura': data.get('temperatura'),
            'pulso': data.get('pulso'),
            'frecuencia_respiratoria': data.get('frecuencia_respiratoria'),
            'presion_arterial': data.get('presion_arterial', ''),
            'motivo_consulta': data.get('motivo_consulta', ''),
            'enfermedad_actual': data.get('enfermedad_actual', ''),
            'fecha_consulta': timezone.now().date(),
            'creado_por': creado_por,
            'activo': True,
        }
        
        nueva_constante = ConstantesVitales(**constante_vital_data)
        nueva_constante.full_clean()
        nueva_constante.save()
        
        logger.info(
            f"Constantes vitales creadas para paciente {paciente.id}"
        )
        
        return nueva_constante
    
    @classmethod
    def tiene_datos_vitales(cls, data):
        """Verifica si hay datos de constantes vitales en el dict"""
        return any(data.get(campo) is not None for campo in cls.VITAL_FIELDS)
    
    @classmethod
    def tiene_datos_texto(cls, data):
        """Verifica si hay datos de texto (motivo/enfermedad) en el dict"""
        return any(data.get(campo) is not None for campo in cls.TEXT_FIELDS)
    
    @classmethod
    def actualizar_constantes_existentes(cls, constante_vital, data):
        """
        Actualiza constantes vitales existentes con nuevos datos
        
        Args:
            constante_vital: Instancia existente de ConstantesVitales
            data: Diccionario con nuevos datos
        """
        if data.get('motivo_consulta') is not None:
            constante_vital.motivo_consulta = data['motivo_consulta']
        
        if data.get('enfermedad_actual') is not None:
            constante_vital.enfermedad_actual = data['enfermedad_actual']
        
        constante_vital.save()
    
    @classmethod
    def obtener_ultima_constante(cls, paciente_id):
        """Obtiene la última constante vital activa de un paciente"""
        return ConstantesVitales.objects.filter(
            paciente_id=paciente_id,
            activo=True
        ).order_by('-fecha_consulta', '-fecha_creacion').first()
    
    @classmethod
    def limpiar_campos_del_dict(cls, data):
        """
        Elimina campos de constantes vitales del diccionario
        para evitar errores al crear ClinicalRecord
        """
        for campo in cls.VITAL_FIELDS + cls.TEXT_FIELDS:
            data.pop(campo, None)
