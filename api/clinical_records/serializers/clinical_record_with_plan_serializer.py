"""
Serializer mejorado para Clinical Record
Incluye datos completos del Plan de Tratamiento con sesiones, diagnósticos, 
procedimientos y prescripciones
"""

from rest_framework import serializers
from api.clinical_records.models import ClinicalRecord
from api.odontogram.models import PlanTratamiento, SesionTratamiento

# Importar el nuevo serializer completo del plan
from api.clinical_records.serializers.plan_tratamiento_serializers import (
    PlanTratamientoCompletoSerializer,
    PlanTratamientoResumenSerializer
)


class ClinicalRecordWithPlanDetailSerializer(serializers.ModelSerializer):
    """
    Serializer COMPLETO de Clinical Record
    Incluye TODOS los datos del Plan de Tratamiento expandidos
    Usar en: retrieve, by-paciente
    """
    
    # Información del paciente
    paciente_info = serializers.SerializerMethodField()
    
    # Información del odontólogo
    odontologo_info = serializers.SerializerMethodField()
    
    # Secciones del historial
    antecedentes_personales_data = serializers.SerializerMethodField()
    antecedentes_familiares_data = serializers.SerializerMethodField()
    constantes_vitales_data = serializers.SerializerMethodField()
    examen_estomatognatico_data = serializers.SerializerMethodField()
    
    plan_tratamiento_completo = serializers.SerializerMethodField()
    
    tiene_plan_tratamiento = serializers.SerializerMethodField()
    
    # Estado del historial
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    puede_editar = serializers.BooleanField(read_only=True)
    esta_completo = serializers.BooleanField(read_only=True)
    indicadores_salud_bucal_data = serializers.SerializerMethodField()
    indices_caries_data = serializers.SerializerMethodField()
    diagnosticos_cie_data = serializers.SerializerMethodField()
    plan_tratamiento_data = serializers.SerializerMethodField()
    
    class Meta:
        model = ClinicalRecord
        fields = [
            # IDs y referencias
            'id',
            'paciente',
            'paciente_info',
            'odontologo_responsable',
            'odontologo_info',
            
            # Números y metadatos
            'numero_historia_clinica_unica',
            'numero_archivo',
            'numero_hoja',
            'institucion_sistema',
            'unicodigo',
            'establecimiento_salud',
            
            # Datos clínicos
            'motivo_consulta',
            'embarazada',
            'enfermedad_actual',
            
            # Secciones
            'antecedentes_personales',
            'antecedentes_personales_data',
            'antecedentes_familiares',
            'antecedentes_familiares_data',
            'constantes_vitales',
            'constantes_vitales_data',
            'examen_estomatognatico',
            'examen_estomatognatico_data',
            
            
            # Indicadores y diagnósticos
            'indicadores_salud_bucal',
            'indicadores_salud_bucal_data',
            'indices_caries',
            'indices_caries_data', 
            'diagnosticos_cie_cargados',
            'tipo_carga_diagnosticos',
            'diagnosticos_cie_data',
            'plan_tratamiento',
            'plan_tratamiento_completo',
            'plan_tratamiento_data', 
            'tiene_plan_tratamiento',
            
            # Estado y metadatos
            'estado',
            'estado_display',
            'fecha_atencion',
            'fecha_cierre',
            'observaciones',
            'puede_editar',
            'esta_completo',
            
            # Flags
            'constantes_vitales_nuevas',
            'motivo_consulta_nuevo',
            'enfermedad_actual_nueva',
            
            # Auditoría
            'activo',
            'fecha_creacion',
            'fecha_modificacion',
        ]
        read_only_fields = [
            'id',
            'numero_historia_clinica_unica',
            'numero_archivo',
            'numero_hoja',
            'fecha_atencion',
            'fecha_cierre',
            'fecha_creacion',
            'fecha_modificacion',
        ]
    
    def get_paciente_info(self, obj):
        """Información básica del paciente"""
        if obj.paciente:
            return {
                'id': str(obj.paciente.id),
                'nombres': obj.paciente.nombres,
                'apellidos': obj.paciente.apellidos,
                'nombre_completo': obj.paciente.nombre_completo,
                'cedula_pasaporte': obj.paciente.cedula_pasaporte,
                'fecha_nacimiento': obj.paciente.fecha_nacimiento,
                'edad': obj.paciente.edad,
                'sexo': obj.paciente.sexo,
            }
        return None
    
    def get_odontologo_info(self, obj):
        """Información del odontólogo responsable"""
        if obj.odontologo_responsable:
            return {
                'id': obj.odontologo_responsable.id,
                'nombres': obj.odontologo_responsable.nombres,
                'apellidos': obj.odontologo_responsable.apellidos,
                'nombre_completo': f"{obj.odontologo_responsable.nombres} {obj.odontologo_responsable.apellidos}",
            }
        return None
    
    def get_antecedentes_personales_data(self, obj):
        """Datos de antecedentes personales"""
        if obj.antecedentes_personales:
            from api.clinical_records.serializers.medical_history import AntecedentesPersonalesSerializer
            return AntecedentesPersonalesSerializer(obj.antecedentes_personales).data
        return None
    
    def get_antecedentes_familiares_data(self, obj):
        """Datos de antecedentes familiares"""
        if obj.antecedentes_familiares:
            from api.clinical_records.serializers.medical_history import AntecedentesFamiliaresSerializer
            return AntecedentesFamiliaresSerializer(obj.antecedentes_familiares).data
        return None
    
    def get_constantes_vitales_data(self, obj):
        """Datos de constantes vitales"""
        if obj.constantes_vitales:
            from api.clinical_records.serializers.vital_signs import ConstantesVitalesSerializer
            return ConstantesVitalesSerializer(obj.constantes_vitales).data
        return None
    
    def get_examen_estomatognatico_data(self, obj):
        """Datos del examen estomatognático"""
        if obj.examen_estomatognatico:
            from api.clinical_records.serializers.stomatognathic_exam import ExamenEstomatognaticoSerializer
            return ExamenEstomatognaticoSerializer(obj.examen_estomatognatico).data
        return None
    
    def get_tiene_plan_tratamiento(self, obj):
        """Verifica si el historial tiene plan de tratamiento"""
        return obj.plan_tratamiento is not None
    
    def get_plan_tratamiento_completo(self, obj):
        """
        DATOS COMPLETOS DEL PLAN DE TRATAMIENTO
        Incluye todas las sesiones con diagnósticos, procedimientos y prescripciones
        """
        if not obj.plan_tratamiento:
            return None
        
        # Usar el serializer completo del plan
        return PlanTratamientoCompletoSerializer(
            obj.plan_tratamiento,
            context=self.context
        ).data
        
    def get_indicadores_salud_bucal_data(self, obj):
        """Datos de indicadores de salud bucal"""
        if obj.indicadores_salud_bucal:
            from api.clinical_records.serializers.oral_health_indicators import OralHealthIndicatorsSerializer
            return OralHealthIndicatorsSerializer(obj.indicadores_salud_bucal).data
        
        # Si no tiene indicadores asociados, buscar los más recientes del paciente
        from api.clinical_records.services.indicadores_service import ClinicalRecordIndicadoresService
        indicadores = ClinicalRecordIndicadoresService.obtener_indicadores_paciente(
            str(obj.paciente_id)
        )
        
        if indicadores:
            from api.clinical_records.serializers.oral_health_indicators import OralHealthIndicatorsSerializer
            return OralHealthIndicatorsSerializer(indicadores).data
        
        return None
    
    def get_indices_caries_data(self, obj):
        """Datos de índices de caries"""
        if obj.indices_caries:
            from api.clinical_records.serializers.indices_caries_serializers import WritableIndicesCariesSerializer
            return WritableIndicesCariesSerializer(obj.indices_caries).data
        
        # Si no tiene índices asociados, buscar los más recientes
        from api.clinical_records.services.indices_caries_service import ClinicalRecordIndicesCariesService
        indices = ClinicalRecordIndicesCariesService.obtener_ultimos_indices(
            str(obj.paciente_id)
        )
        
        if indices:
            from api.clinical_records.serializers.indices_caries_serializers import WritableIndicesCariesSerializer
            return WritableIndicesCariesSerializer(indices).data
        
        return None
    
    def get_diagnosticos_cie_data(self, obj):
        """Datos de diagnósticos CIE"""
        from api.clinical_records.services.diagnostico_cie_service import DiagnosticosCIEService
        diagnosticos = DiagnosticosCIEService.obtener_diagnosticos_historial(str(obj.id))
        
        if diagnosticos:
            # Filtrar solo activos
            diagnosticos_activos = [d for d in diagnosticos if d.get('activo', True)]
            
            return {
                'diagnosticos': diagnosticos_activos,
                'tipo_carga': obj.tipo_carga_diagnosticos or 'nuevos',
                'total': len(diagnosticos_activos),
                'total_inactivos': len(diagnosticos) - len(diagnosticos_activos)
            }
        
        return None
    
    def get_plan_tratamiento_data(self, obj):
        if not obj.plan_tratamiento:
            return None
        
        try:
            # Serializar el plan histórico con todos sus datos
            serializer = PlanTratamientoCompletoSerializer(
                obj.plan_tratamiento,
                context=self.context
            )
            return serializer.data
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error serializando plan histórico del historial {obj.id}: {str(e)}")
            return None


class ClinicalRecordListSerializer(serializers.ModelSerializer):
    """
    Serializer para listados de Clinical Record
    Versión ligera con resumen del plan
    """
    
    paciente_info = serializers.SerializerMethodField()
    odontologo_info = serializers.SerializerMethodField()
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    
    # Plan de tratamiento: solo resumen
    plan_tratamiento_resumen = serializers.SerializerMethodField()
    tiene_plan_tratamiento = serializers.SerializerMethodField()
    
    class Meta:
        model = ClinicalRecord
        fields = [
            'id',
            'numero_historia_clinica_unica',
            'paciente',
            'paciente_info',
            'odontologo_responsable',
            'odontologo_info',
            'motivo_consulta',
            'estado',
            'estado_display',
            'fecha_atencion',
            'tiene_plan_tratamiento',
            'plan_tratamiento_resumen',
            'activo',
        ]
    
    def get_paciente_info(self, obj):
        """Información básica del paciente"""
        if obj.paciente:
            return {
                'id': str(obj.paciente.id),
                'nombre_completo': obj.paciente.nombre_completo,
                'cedula_pasaporte': obj.paciente.cedula_pasaporte,
            }
        return None
    
    def get_odontologo_info(self, obj):
        """Información del odontólogo"""
        if obj.odontologo_responsable:
            return {
                'id': obj.odontologo_responsable.id,
                'nombre_completo': f"{obj.odontologo_responsable.nombres} {obj.odontologo_responsable.apellidos}",
            }
        return None
    
    def get_tiene_plan_tratamiento(self, obj):
        """Verifica si tiene plan"""
        return obj.plan_tratamiento is not None
    
    def get_plan_tratamiento_resumen(self, obj):
        """Resumen del plan (sin sesiones completas)"""
        if not obj.plan_tratamiento:
            return None
        
        return PlanTratamientoResumenSerializer(obj.plan_tratamiento).data


class ClinicalRecordCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para crear Clinical Record
    Permite especificar plan_tratamiento o se vincula automáticamente
    """
    
    # Permitir especificar el plan (opcional)
    plan_tratamiento = serializers.PrimaryKeyRelatedField(
        queryset=PlanTratamiento.objects.filter(activo=True),
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = ClinicalRecord
        fields = [
            'paciente',
            'odontologo_responsable',
            'motivo_consulta',
            'embarazada',
            'enfermedad_actual',
            'antecedentes_personales',
            'antecedentes_familiares',
            'constantes_vitales',
            'examen_estomatognatico',
            'indicadores_salud_bucal',
            'indices_caries',
            'plan_tratamiento', 
            'observaciones',
            'establecimiento_salud',
            'unicodigo',
        ]