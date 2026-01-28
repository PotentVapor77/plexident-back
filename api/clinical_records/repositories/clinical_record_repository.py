from django.db.models import Q, Prefetch
from api.clinical_records.models import ClinicalRecord


class ClinicalRecordRepository:
    """Repositorio para operaciones de acceso a datos de Historiales Clínicos"""

    @staticmethod
    def obtener_todos(activo=True):
        """Obtiene todos los historiales clínicos con relaciones precargadas"""
        queryset = ClinicalRecord.objects.select_related(
            'paciente',
            'odontologo_responsable',
            'antecedentes_personales',
            'antecedentes_familiares',
            'constantes_vitales',
            'examen_estomatognatico',
            'creado_por',
            'actualizado_por'
        )
        
        if activo is not None:
            queryset = queryset.filter(activo=activo)
        
        return queryset.order_by('-fecha_atencion')

    @staticmethod
    def obtener_por_id(clinical_record_id):
        """Obtiene un historial clínico por ID"""
        return ClinicalRecord.objects.select_related(
            'paciente',
            'odontologo_responsable',
            'antecedentes_personales',
            'antecedentes_familiares',
            'constantes_vitales',
            'examen_estomatognatico'
        ).get(id=clinical_record_id)

    @staticmethod
    def obtener_por_paciente(paciente_id, activo=True):
        """Obtiene todos los historiales de un paciente"""
        queryset = ClinicalRecord.objects.filter(
            paciente_id=paciente_id
        ).select_related(
            'odontologo_responsable',
            'antecedentes_personales',
            'antecedentes_familiares',
            'constantes_vitales',
            'examen_estomatognatico'
        )
        
        if activo is not None:
            queryset = queryset.filter(activo=activo)
        
        return queryset.order_by('-fecha_atencion')

    @staticmethod
    def obtener_por_odontologo(odontologo_id, activo=True):
        """Obtiene todos los historiales de un odontólogo"""
        queryset = ClinicalRecord.objects.filter(
            odontologo_responsable_id=odontologo_id
        ).select_related('paciente')
        
        if activo is not None:
            queryset = queryset.filter(activo=activo)
        
        return queryset.order_by('-fecha_atencion')

    @staticmethod
    def buscar(query, activo=True):
        """Búsqueda de historiales por diferentes criterios"""
        queryset = ClinicalRecord.objects.filter(
            Q(paciente__nombres__icontains=query) |
            Q(paciente__apellidos__icontains=query) |
            Q(paciente__cedula_pasaporte__icontains=query) |
            Q(motivo_consulta__icontains=query) |
            Q(odontologo_responsable__nombres__icontains=query) |
            Q(odontologo_responsable__apellidos__icontains=query)
        ).select_related('paciente', 'odontologo_responsable')
        
        if activo is not None:
            queryset = queryset.filter(activo=activo)
        
        return queryset.order_by('-fecha_atencion')

    @staticmethod
    def obtener_ultimos_datos_paciente(paciente_id):
        """
        Obtiene los últimos datos guardados de todas las secciones de un paciente.
        Se usa para pre-cargar el formulario de historial clínico.
        """
        from api.patients.models.antecedentes_personales import AntecedentesPersonales
        from api.patients.models.antecedentes_familiares import AntecedentesFamiliares
        from api.patients.models.constantes_vitales import ConstantesVitales
        from api.patients.models.examen_estomatognatico import ExamenEstomatognatico
        
        return {
            'antecedentes_personales': AntecedentesPersonales.objects.filter(
                paciente_id=paciente_id,
                activo=True
            ).order_by('-fecha_creacion').first(),
            'antecedentes_familiares': AntecedentesFamiliares.objects.filter(
                paciente_id=paciente_id,
                activo=True
            ).order_by('-fecha_creacion').first(),
            'constantes_vitales': ConstantesVitales.objects.filter(
                paciente_id=paciente_id,
                activo=True
            ).order_by('-fecha_creacion').first(),
            'examen_estomatognatico': ExamenEstomatognatico.objects.filter(
                paciente_id=paciente_id,
                activo=True
            ).order_by('-fecha_creacion').first(),
        }
