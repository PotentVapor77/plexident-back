from django.utils import timezone
from django.core.exceptions import ValidationError
from api.clinical_records.repositories import ClinicalRecordRepository
from api.clinical_records.models import ClinicalRecord
from api.patients.models.paciente import Paciente
from api.patients.models.constantes_vitales import ConstantesVitales

class ClinicalRecordService:
    """Servicio para la lógica de negocio de Historiales Clínicos"""

    @staticmethod
    def crear_historial(data):
        """
        Crea un nuevo historial clínico.
        Pre-carga los últimos datos guardados del paciente.
        """
        paciente = data.get('paciente')
        paciente_id = paciente.id
        
        # Obtener últimos datos guardados
        ultimos_datos = ClinicalRecordRepository.obtener_ultimos_datos_paciente(paciente_id)
        ultima_constante_vital = ConstantesVitales.objects.filter(paciente_id=paciente_id,activo=True).first()
        
        # Pre-cargar datos del paciente en el historial
        if not data.get('motivo_consulta'):
            data['motivo_consulta'] = ultima_constante_vital.motivo_consulta or ''
        
        if not data.get('embarazada'):
            data['embarazada'] = paciente.embarazada
        
        if not data.get('enfermedad_actual'):
            data['enfermedad_actual'] = ultima_constante_vital.enfermedad_actual or ''
        
        # Asignar referencias a últimos datos si no se proporcionan
        if not data.get('antecedentes_personales') and ultimos_datos['antecedentes_personales']:
            data['antecedentes_personales'] = ultimos_datos['antecedentes_personales']
        
        if not data.get('antecedentes_familiares') and ultimos_datos['antecedentes_familiares']:
            data['antecedentes_familiares'] = ultimos_datos['antecedentes_familiares']
        
        if not data.get('constantes_vitales') and ultimos_datos['constantes_vitales']:
            data['constantes_vitales'] = ultimos_datos['constantes_vitales']
        
        if not data.get('examen_estomatognatico') and ultimos_datos['examen_estomatognatico']:
            data['examen_estomatognatico'] = ultimos_datos['examen_estomatognatico']
        
        # Crear historial
        historial = ClinicalRecord(**data)
        historial.full_clean()
        historial.save()
        
        return historial

    @staticmethod
    def actualizar_historial(historial_id, data):
        """
        Actualiza un historial clínico existente.
        No permite edición si está cerrado.
        """
        historial = ClinicalRecordRepository.obtener_por_id(historial_id)
        
        if historial.estado == 'CERRADO':
            raise ValidationError('No se puede editar un historial cerrado.')
        
        # Actualizar campos
        for key, value in data.items():
            if hasattr(historial, key) and key not in ['id', 'fecha_atencion', 'fecha_cierre']:
                setattr(historial, key, value)
        
        historial.full_clean()
        historial.save()
        
        return historial

    @staticmethod
    def cerrar_historial(historial_id, usuario):
        """
        Cierra un historial clínico, impidiendo futuras ediciones.
        """
        historial = ClinicalRecordRepository.obtener_por_id(historial_id)
        historial.cerrar_historial(usuario)
        return historial

    @staticmethod
    def reabrir_historial(historial_id, usuario):
        """
        Reabre un historial cerrado (acción sensible, requiere permisos).
        """
        historial = ClinicalRecordRepository.obtener_por_id(historial_id)
        historial.reabrir_historial(usuario)
        return historial

    @staticmethod
    def eliminar_historial(historial_id):
        """Eliminación lógica de un historial"""
        historial = ClinicalRecordRepository.obtener_por_id(historial_id)
        historial.activo = False
        historial.save()
        return historial

    @staticmethod
    def obtener_historial_con_datos_completos(historial_id):
        """
        Obtiene un historial con todas sus relaciones cargadas.
        Útil para vistas detalladas.
        """
        return ClinicalRecordRepository.obtener_por_id(historial_id)

    @staticmethod
    def cargar_datos_iniciales_paciente(paciente_id):
        """
        Carga los últimos datos guardados de un paciente con datos completos
        para permitir la edición durante la creación del historial.
        """
        from api.patients.serializers import (
            AntecedentesPersonalesSerializer,
            AntecedentesFamiliaresSerializer,
            ConstantesVitalesSerializer,
            ExamenEstomatognaticoSerializer
        )
        
        paciente = Paciente.objects.get(id=paciente_id)
        ultimos_datos = ClinicalRecordRepository.obtener_ultimos_datos_paciente(paciente_id)
        ultima_constante_vital = ConstantesVitales.objects.filter(paciente_id=paciente_id,activo=True).first()        
        def format_date(obj):
            if obj and hasattr(obj, 'fecha_creacion'):
                return obj.fecha_creacion.isoformat()
            if obj and hasattr(obj, 'fecha_consulta'):
                return obj.fecha_consulta.isoformat()
            return None
        
        # Serializar los datos completos de cada sección
        antecedentes_personales_data = None
        if ultimos_datos['antecedentes_personales']:
            antecedentes_personales_data = AntecedentesPersonalesSerializer(
                ultimos_datos['antecedentes_personales']
            ).data
        
        antecedentes_familiares_data = None
        if ultimos_datos['antecedentes_familiares']:
            antecedentes_familiares_data = AntecedentesFamiliaresSerializer(
                ultimos_datos['antecedentes_familiares']
            ).data
        
        constantes_vitales_data = None
        if ultimos_datos['constantes_vitales']:
            constantes_vitales_data = ConstantesVitalesSerializer(
                ultimos_datos['constantes_vitales']
            ).data
        
        examen_estomatognatico_data = None
        if ultimos_datos['examen_estomatognatico']:
            examen_estomatognatico_data = ExamenEstomatognaticoSerializer(
                ultimos_datos['examen_estomatognatico']
            ).data
        
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
            'motivo_consulta':  ultima_constante_vital.motivo_consulta if  ultima_constante_vital else '',
            'motivo_consulta_fecha': format_date( ultima_constante_vital),
            
            'embarazada': paciente.embarazada,
            
            'enfermedad_actual':  ultima_constante_vital.enfermedad_actual if  ultima_constante_vital else '',
            'enfermedad_actual_fecha': format_date( ultima_constante_vital),
            
            # Datos completos de cada sección con metadata
            'antecedentes_personales': {
                'id': str(ultimos_datos['antecedentes_personales'].id) if ultimos_datos['antecedentes_personales'] else None,
                'fecha': format_date(ultimos_datos['antecedentes_personales']),
                'data': antecedentes_personales_data
            },
            
            'antecedentes_familiares': {
                'id': str(ultimos_datos['antecedentes_familiares'].id) if ultimos_datos['antecedentes_familiares'] else None,
                'fecha': format_date(ultimos_datos['antecedentes_familiares']),
                'data': antecedentes_familiares_data
            },
            
            'constantes_vitales': {
                'id': str(ultimos_datos['constantes_vitales'].id) if ultimos_datos['constantes_vitales'] else None,
                'fecha': format_date(ultimos_datos['constantes_vitales']),
                'data': constantes_vitales_data
            },
            
            'examen_estomatognatico': {
                'id': str(ultimos_datos['examen_estomatognatico'].id) if ultimos_datos['examen_estomatognatico'] else None,
                'fecha': format_date(ultimos_datos['examen_estomatognatico']),
                'data': examen_estomatognatico_data
            }
        }