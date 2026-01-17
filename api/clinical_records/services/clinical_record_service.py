from django.utils import timezone
from django.core.exceptions import ValidationError
from api.clinical_records.repositories import ClinicalRecordRepository
from api.clinical_records.models import ClinicalRecord
from api.patients.models.paciente import Paciente


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
        
        # Pre-cargar datos del paciente en el historial
        if not data.get('motivo_consulta'):
            data['motivo_consulta'] = paciente.motivo_consulta or ''
        
        if not data.get('embarazada'):
            data['embarazada'] = paciente.embarazada
        
        if not data.get('enfermedad_actual'):
            data['enfermedad_actual'] = paciente.enfermedad_actual or ''
        
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
        Carga los últimos datos guardados de un paciente.
        Se usa en el frontend para pre-llenar el formulario.
        """
        paciente = Paciente.objects.get(id=paciente_id)
        ultimos_datos = ClinicalRecordRepository.obtener_ultimos_datos_paciente(paciente_id)
        
        return {
            'paciente': {
                'id': str(paciente.id),
                'nombre_completo': paciente.nombre_completo,
                'cedula_pasaporte': paciente.cedula_pasaporte,
                'sexo': paciente.sexo,
                'edad': paciente.edad,
            },
            'motivo_consulta': paciente.motivo_consulta or '',
            'embarazada': paciente.embarazada,
            'enfermedad_actual': paciente.enfermedad_actual or '',
            'antecedentes_personales_id': str(ultimos_datos['antecedentes_personales'].id) if ultimos_datos['antecedentes_personales'] else None,
            'antecedentes_familiares_id': str(ultimos_datos['antecedentes_familiares'].id) if ultimos_datos['antecedentes_familiares'] else None,
            'constantes_vitales_id': str(ultimos_datos['constantes_vitales'].id) if ultimos_datos['constantes_vitales'] else None,
            'examen_estomatognatico_id': str(ultimos_datos['examen_estomatognatico'].id) if ultimos_datos['examen_estomatognatico'] else None,
        }
