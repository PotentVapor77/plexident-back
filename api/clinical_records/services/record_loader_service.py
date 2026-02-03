# api/clinical_records/services/record_loader_service.py

"""
Servicio para carga de datos iniciales de historiales
"""
import logging
from api.patients.models.paciente import Paciente
from api.patients.models.constantes_vitales import ConstantesVitales
from api.clinical_records.models import ClinicalRecord
from api.clinical_records.repositories import ClinicalRecordRepository
from api.patients.serializers import (
    AntecedentesPersonalesSerializer,
    AntecedentesFamiliaresSerializer,
    ConstantesVitalesSerializer,
    ExamenEstomatognaticoSerializer,
)
from api.clinical_records.config import INSTITUCION_CONFIG
from api.clinical_records.serializers.indices_caries_serializers import IndicesCariesSerializer
from api.clinical_records.services.indices_caries_service import ClinicalRecordIndicesCariesService
from .number_generator_service import NumberGeneratorService
# AGREGAR ESTAS IMPORTACIONES:
from .indicadores_service import ClinicalRecordIndicadoresService
from api.clinical_records.serializers.oral_health_indicators import OralHealthIndicatorsSerializer


logger = logging.getLogger(__name__)


class RecordLoaderService:
    """Servicio para cargar datos pre-existentes de pacientes"""
    
    @staticmethod
    def format_date(obj):
        """Formatea fecha de un objeto"""
        if obj and hasattr(obj, 'fecha_creacion'):
            return obj.fecha_creacion.isoformat()
        if obj and hasattr(obj, 'fecha_consulta'):
            return obj.fecha_consulta.isoformat()
        if obj and hasattr(obj, 'fecha'):
            return obj.fecha.isoformat()
        return None
    
    @classmethod
    def cargar_datos_iniciales_paciente(cls, paciente_id):
        """
        Carga los últimos datos guardados de un paciente
        para prellenar el formulario de creación de historial
        """
        try:
            paciente = Paciente.objects.get(id=paciente_id)
        except Paciente.DoesNotExist:
            raise ValueError(f"Paciente {paciente_id} no encontrado")
        
        # Obtener últimos datos del paciente
        ultimos_datos = ClinicalRecordRepository.obtener_ultimos_datos_paciente(
            paciente_id
        )
        
        # Obtener última constante vital
        ultima_constante = ConstantesVitales.objects.filter(
            paciente_id=paciente_id,
            activo=True
        ).order_by('-fecha_consulta', '-fecha_creacion').first()
        
        ultimo_historial = ClinicalRecord.objects.filter(
            paciente_id=paciente_id,
            activo=True
        ).order_by('-fecha_atencion').first()
        
        # AGREGAR: Obtener indicadores de salud bucal más recientes
        indicadores = ClinicalRecordIndicadoresService.obtener_indicadores_paciente(paciente_id)
        
        # Generar números automáticos
        numero_historia_unica = (
            NumberGeneratorService.generar_numero_historia_clinica_unica()
        )
        numero_archivo = NumberGeneratorService.generar_numero_archivo(
            paciente_id
        )
        
        if ultimo_historial:
            # Tomar valores del último historial
            institucion_sistema = ultimo_historial.institucion_sistema
            unicodigo = INSTITUCION_CONFIG['UNICODIGO_DEFAULT']
            establecimiento_salud = ultimo_historial.establecimiento_salud
            numero_hoja = ultimo_historial.numero_hoja + 1
        else:
            # Valores por defecto para primer historial
            institucion_sistema = "SISTEMA NACIONAL DE SALUD"
            unicodigo = "1213141516001-150"  # Valor por defecto
            establecimiento_salud = "FamySALUD"  
            numero_hoja = 1
            
        # Serializar datos completos de cada sección
        antecedentes_personales_data = cls._serializar_seccion(
            ultimos_datos.get('antecedentes_personales'),
            AntecedentesPersonalesSerializer,
            'antecedentes personales'
        )
        
        antecedentes_familiares_data = cls._serializar_seccion(
            ultimos_datos.get('antecedentes_familiares'),
            AntecedentesFamiliaresSerializer,
            'antecedentes familiares'
        )
        
        constantes_vitales_data = cls._serializar_seccion(
            ultimos_datos.get('constantes_vitales'),
            ConstantesVitalesSerializer,
            'constantes vitales'
        )
        
        examen_estomatognatico_data = cls._serializar_seccion(
            ultimos_datos.get('examen_estomatognatico'),
            ExamenEstomatognaticoSerializer,
            'examen estomatognático'
        )
        
        indicadores_salud_bucal_data = cls._serializar_seccion(
            indicadores,
            OralHealthIndicatorsSerializer,
            'indicadores de salud bucal'
        )
        
        indices_caries = ClinicalRecordIndicesCariesService.obtener_ultimos_indices(paciente_id)
        
        indices_caries_data = cls._serializar_seccion(
            indices_caries,
            IndicesCariesSerializer,  
            'índices de caries'
        )
        indices_caries_formatted = cls._formatear_seccion(
            indices_caries,
            indices_caries_data,
        )
        return {
            # Información del paciente
            'paciente': {
                'id': str(paciente.id),
                'nombre_completo': paciente.nombre_completo,
                'cedula_pasaporte': paciente.cedula_pasaporte,
                'sexo': paciente.sexo,
                'edad': paciente.edad,
            },
            
            # Datos de texto editables
            'motivo_consulta': (
                ultima_constante.motivo_consulta if ultima_constante else ''
            ),
            'motivo_consulta_fecha': cls.format_date(ultima_constante),
            'embarazada': paciente.embarazada,
            'enfermedad_actual': (
                ultima_constante.enfermedad_actual if ultima_constante else ''
            ),
            'enfermedad_actual_fecha': cls.format_date(ultima_constante),
            
            # Campos del formulario
            'campos_formulario': {
                'institucion_sistema': institucion_sistema,
                'unicodigo': unicodigo,
                'establecimiento_salud': establecimiento_salud,
                'numero_historia_clinica_unica': numero_historia_unica,
                'numero_archivo': numero_archivo,
                'numero_hoja': numero_hoja,
            },
            
            # Datos completos de cada sección
            'antecedentes_personales': cls._formatear_seccion(
                ultimos_datos.get('antecedentes_personales'),
                antecedentes_personales_data
            ),
            'antecedentes_familiares': cls._formatear_seccion(
                ultimos_datos.get('antecedentes_familiares'),
                antecedentes_familiares_data
            ),
            'constantes_vitales': cls._formatear_seccion(
                ultimos_datos.get('constantes_vitales'),
                constantes_vitales_data
            ),
            'examen_estomatognatico': cls._formatear_seccion(
                ultimos_datos.get('examen_estomatognatico'),
                examen_estomatognatico_data
            ),
            'indicadores_salud_bucal': cls._formatear_seccion(
                indicadores,
                indicadores_salud_bucal_data
            ),
            'indices_caries': indices_caries_formatted,
        }
    
    @staticmethod
    def _serializar_seccion(instancia, serializer_class, nombre_seccion):
        """Serializa una sección de datos manejando errores"""
        if not instancia:
            return None
        
        try:
            return serializer_class(instancia).data
        except Exception as e:
            logger.error(f"Error serializando {nombre_seccion}: {e}")
            return None
    
    @classmethod
    def _formatear_seccion(cls, instancia, data_serializada):
        """Formatea una sección con metadata"""
        if not instancia:
            return {'id': None, 'fecha': None, 'data': None}
        
        return {
            'id': str(instancia.id),
            'fecha': cls.format_date(instancia),
            'data': data_serializada
        }
