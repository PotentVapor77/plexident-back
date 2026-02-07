# src/api/clinical_records/serializers/clinical_record.py

"""
Serializers principales para Clinical Record
"""
from rest_framework import serializers
from django.utils import timezone
import logging

from api.clinical_records.models import ClinicalRecord
from api.patients.models.paciente import Paciente
from api.patients.models.antecedentes_personales import AntecedentesPersonales
from api.patients.models.antecedentes_familiares import AntecedentesFamiliares
from api.patients.models.constantes_vitales import ConstantesVitales
from api.patients.models.examen_estomatognatico import ExamenEstomatognatico
from api.clinical_records.config import INSTITUCION_CONFIG
from api.clinical_records.serializers.form033_snapshot_serializer import Form033SnapshotSerializer
from api.clinical_records.serializers.oral_health_indicators import OralHealthIndicatorsSerializer
from api.clinical_records.serializers.indices_caries_serializers import WritableIndicesCariesSerializer
from api.clinical_records.serializers.diagnosticos_cie_serializers import WritableDiagnosticoCIEHistorialSerializer
from api.clinical_records.services.diagnostico_cie_service import DiagnosticosCIEService
from api.odontogram.serializers.plan_tratamiento_serializers import PlanTratamientoDetailSerializer
from api.odontogram.models import PlanTratamiento

from .base import DateFormatterMixin
from .patient_data import PatientInfoMixin
from .medical_history import (
    WritableAntecedentesPersonalesSerializer,
    WritableAntecedentesFamiliaresSerializer,
)
from .vital_signs import (
    WritableConstantesVitalesSerializer,
    VitalSignsFieldsMixin,
)
from .stomatognathic_exam import WritableExamenEstomatognaticoSerializer

logger = logging.getLogger(__name__)


class ClinicalRecordSerializer(serializers.ModelSerializer):
    """Serializer básico para listado de historiales clínicos"""
    
    paciente_nombre = serializers.CharField(
        source='paciente.nombre_completo', 
        read_only=True
    )
    paciente_cedula = serializers.CharField(
        source='paciente.cedula_pasaporte', 
        read_only=True
    )
    odontologo_nombre = serializers.CharField(
        source='odontologo_responsable.get_full_name', 
        read_only=True
    )
    estado_display = serializers.CharField(
        source='get_estado_display', 
        read_only=True
    )
    puede_editar = serializers.BooleanField(read_only=True)
    esta_completo = serializers.BooleanField(read_only=True)
    indicadores_salud = OralHealthIndicatorsSerializer(read_only=True)
    class Meta:
        model = ClinicalRecord
        fields = [
            'id',
            'paciente',
            'paciente_nombre',
            'paciente_cedula',
            'odontologo_responsable',
            'odontologo_nombre',
            'fecha_atencion',
            'fecha_creacion',
            'fecha_cierre',
            'estado',
            'estado_display',
            'motivo_consulta',
            'activo',
            'puede_editar',
            'esta_completo',
            'indicadores_salud',
            'indices_caries',
            
            
        ]
        read_only_fields = (
            'id',
            'creado_por',
            'actualizado_por',
            'fecha_creacion',
            'fecha_modificacion',
            'fecha_atencion',
            'fecha_cierre',
        )
    
    
    
    def to_representation(self, instance):
        """
        Consolidación de representaciones para lista.
        """
        data = super().to_representation(instance)
        
        # 1. Formatear fechas
        date_fields = ['fecha_atencion', 'fecha_cierre', 'fecha_creacion', 'fecha_modificacion']
        for field in date_fields:
            val = getattr(instance, field, None)
            if val:
                data[field] = val.isoformat()

        # 2. Constantes Vitales
        if instance.constantes_vitales:
            cv_serializer = WritableConstantesVitalesSerializer(instance.constantes_vitales)
            data['constantes_vitales_data'] = cv_serializer.data
            if instance.constantes_vitales.fecha_consulta:
                data['constantes_vitales_data']['fecha_consulta'] = instance.constantes_vitales.fecha_consulta.isoformat()

        if instance.indicadores_salud_bucal:
            # Usar los indicadores asociados a este historial
            data['indicadores_salud_bucal_data'] = OralHealthIndicatorsSerializer(
                instance.indicadores_salud_bucal
            ).data
            print(f"Lista - Usando indicadores FK para historial {instance.id}")
        else:
            # Fallback: buscar los últimos del paciente
            from api.clinical_records.services.indicadores_service import ClinicalRecordIndicadoresService
            indicadores_latest = ClinicalRecordIndicadoresService.obtener_indicadores_paciente(
                str(instance.paciente_id)
            )
            if indicadores_latest:
                data['indicadores_salud_bucal_data'] = OralHealthIndicatorsSerializer(
                    indicadores_latest
                ).data
                print(f"Lista - Usando indicadores más recientes para paciente")
            else:
                data['indicadores_salud_bucal_data'] = None
                
        
        if instance.indices_caries:
            data["indices_caries_data"] = WritableIndicesCariesSerializer(
                instance.indices_caries
            ).data
        else:
            data["indices_caries_data"] = None
        
        if instance.plan_tratamiento:
            from api.odontogram.serializers.plan_tratamiento_serializers import PlanTratamientoDetailSerializer
            
            plan_serializer = PlanTratamientoDetailSerializer(
                instance.plan_tratamiento,
                context={'include_sesiones': True, 'include_detalle_completo': True}
            )
            data['plan_tratamiento_data'] = plan_serializer.data
            
            # Consolidar procedimientos y prescripciones de todas las sesiones
            procedimientos_consolidados = []
            prescripciones_consolidadas = []
            sesiones_detalle = []
            
            for sesion in plan_serializer.data.get('sesiones', []):
                sesion_detalle = {
                    'numero_sesion': sesion.get('numero_sesion'),
                    'fecha_programada': sesion.get('fecha_programada'),
                    'estado': sesion.get('estado'),
                    'estado_display': sesion.get('estado_display'),
                    'diagnosticos_complicaciones': sesion.get('diagnosticos_complicaciones', []),
                    'procedimientos': sesion.get('procedimientos', []),
                    'prescripciones': sesion.get('prescripciones', []),
                    'notas': sesion.get('notas'),
                    'observaciones': sesion.get('observaciones'),
                }
                sesiones_detalle.append(sesion_detalle)
                
                # Consolidar para vista general
                if sesion.get('procedimientos'):
                    procedimientos_consolidados.extend(sesion['procedimientos'])
                
                if sesion.get('prescripciones'):
                    prescripciones_consolidadas.extend(sesion['prescripciones'])
            
            data['plan_tratamiento_sesiones_detalle'] = sesiones_detalle
            data['plan_tratamiento_procedimientos_consolidados'] = procedimientos_consolidados
            data['plan_tratamiento_prescripciones_consolidadas'] = prescripciones_consolidadas
            
            # Generar resumen de prescripciones (texto consolidado)
            if prescripciones_consolidadas:
                texto_prescripciones = "Prescripciones:\n"
                for i, prescripcion in enumerate(prescripciones_consolidadas, 1):
                    texto_prescripciones += f"{i}. {prescripcion.get('medicamento', '')} - "
                    texto_prescripciones += f"{prescripcion.get('dosis', '')} - "
                    texto_prescripciones += f"{prescripcion.get('frecuencia', '')}\n"
                    if prescripcion.get('observaciones'):
                        texto_prescripciones += f"   Obs: {prescripcion['observaciones']}\n"
                data['plan_tratamiento_texto_prescripciones'] = texto_prescripciones
            else:
                data['plan_tratamiento_texto_prescripciones'] = "No hay prescripciones registradas."
        
        # 4. Campos institucionales
        data['institucion_sistema'] = instance.institucion_sistema or "SISTEMA NACIONAL DE SALUD"
        data['unicodigo'] = instance.unicodigo or ""
        data['establecimiento_salud'] = instance.establecimiento_salud or ""
        data['numero_hoja'] = instance.numero_hoja or 1
        data['numero_historia_clinica_unica'] = instance.numero_historia_clinica_unica or ""
        data['numero_archivo'] = instance.numero_archivo or ""

        return data


class ClinicalRecordDetailSerializer(
    DateFormatterMixin,
    PatientInfoMixin,
    VitalSignsFieldsMixin,
    serializers.ModelSerializer
):
    """Serializer detallado con capacidad de escritura anidada"""
    
    numero_historia_clinica_unica = serializers.CharField(read_only=True)
    numero_archivo = serializers.CharField(read_only=True)
    #indicadores_salud_bucal = serializers.SerializerMethodField()
    tiene_indicadores = serializers.BooleanField(read_only=True)
    # Información expandida (read-only)
    paciente_info = serializers.SerializerMethodField()
    odontologo_info = serializers.SerializerMethodField()
    creado_por_info = serializers.SerializerMethodField()
    
    
    # Secciones expandidas - WRITABLE
    antecedentes_personales_data = WritableAntecedentesPersonalesSerializer(
        source='antecedentes_personales', 
        required=False, 
        allow_null=True
    )
    antecedentes_familiares_data = WritableAntecedentesFamiliaresSerializer(
        source='antecedentes_familiares', 
        required=False, 
        allow_null=True
    )
    constantes_vitales_data = WritableConstantesVitalesSerializer(
        source='constantes_vitales',
        required=False,
        allow_null=True,
        read_only=True, 
    )
    examen_estomatognatico_data = WritableExamenEstomatognaticoSerializer(
        source='examen_estomatognatico', 
        required=False, 
        allow_null=True
    )
    
    estado_display = serializers.CharField(
        source='get_estado_display', 
        read_only=True
    )
    
    puede_editar = serializers.BooleanField(read_only=True)
    esta_completo = serializers.BooleanField(read_only=True)
    form033_snapshot = Form033SnapshotSerializer(read_only=True)
    tiene_odontograma = serializers.BooleanField(read_only=True)
    
    indices_caries_data = WritableIndicesCariesSerializer(
        source='indices_caries',
        required=False,
        allow_null=True
    )
    
    diagnosticos_cie_data = WritableDiagnosticoCIEHistorialSerializer(
        source='diagnosticos_cie',
        required=False,
        allow_null=True,
        read_only=True
    )
    plan_tratamiento = serializers.PrimaryKeyRelatedField(
        queryset=PlanTratamiento.objects.filter(activo=True),
        required=False,
        allow_null=True
    )
    diagnosticos_cie_cargados = serializers.BooleanField(read_only=True)
    tipo_carga_diagnosticos = serializers.CharField(read_only=True)
    
    plan_tratamiento = PlanTratamientoDetailSerializer(read_only=True)
    
    class Meta:
        model = ClinicalRecord
        fields = '__all__'
        read_only_fields = (
            'id',
            'creado_por',
            'actualizado_por',
            'fecha_creacion',
            'fecha_modificacion',
            'fecha_atencion',
            'fecha_cierre',
            'paciente',
            'numero_historia_clinica_unica',
            'numero_archivo',
            'form033_snapshot', 
            'tiene_odontograma',
            'indices_caries',
            'indices_caries_data',
            'plan_tratamiento',
        )
    
    def update(self, instance, validated_data):
        """Manejar actualizaciones con lógica de versionado"""
        
        # 1. Extraer campos individuales de constantes vitales
        temperatura = validated_data.pop('temperatura', None)
        pulso = validated_data.pop('pulso', None)
        frecuencia_respiratoria = validated_data.pop('frecuencia_respiratoria', None)
        presion_arterial = validated_data.pop('presion_arterial', None)
        motivo_consulta_texto = validated_data.pop('motivo_consulta_texto', None)
        enfermedad_actual_texto = validated_data.pop('enfermedad_actual_texto', None)
        
        # 2. Extraer campos directos
        motivo_consulta_directo = validated_data.pop('motivo_consulta', None)
        enfermedad_actual_directo = validated_data.pop('enfermedad_actual', None)
        
        # 3. Extraer datos anidados
        antecedentes_personales_data = validated_data.pop(
            'antecedentes_personales', None
        )
        antecedentes_familiares_data = validated_data.pop(
            'antecedentes_familiares', None
        )
        examen_estomatognatico_data = validated_data.pop(
            'examen_estomatognatico', None
        )
        
        # 4. Determinar valores finales
        motivo_final = (
            motivo_consulta_texto 
            if motivo_consulta_texto is not None 
            else motivo_consulta_directo
        )
        enfermedad_final = (
            enfermedad_actual_texto 
            if enfermedad_actual_texto is not None 
            else enfermedad_actual_directo
        )
        
        # 5. Verificar cambios en constantes vitales
        hay_cambios_constantes = any([
            temperatura is not None,
            pulso is not None,
            frecuencia_respiratoria is not None,
            presion_arterial is not None,
            motivo_final is not None,
            enfermedad_final is not None,
        ])
        
        # 6. Crear nuevas constantes vitales si hay cambios
        if hay_cambios_constantes:
            cv_actual = instance.constantes_vitales
            
            nueva_cv_data = {
                'paciente': instance.paciente,
                'temperatura': (
                    temperatura 
                    if temperatura is not None 
                    else getattr(cv_actual, 'temperatura', None)
                ),
                'pulso': (
                    pulso 
                    if pulso is not None 
                    else getattr(cv_actual, 'pulso', None)
                ),
                'frecuencia_respiratoria': (
                    frecuencia_respiratoria
                    if frecuencia_respiratoria is not None
                    else getattr(cv_actual, 'frecuencia_respiratoria', None)
                ),
                'presion_arterial': (
                    presion_arterial
                    if presion_arterial is not None
                    else getattr(cv_actual, 'presion_arterial', '')
                ),
                'fecha_consulta': timezone.now().date(),
                'creado_por': self.context['request'].user,
                'activo': True,
            }
            
            if motivo_final is not None:
                nueva_cv_data['motivo_consulta'] = motivo_final
                instance.motivo_consulta = motivo_final
                instance.motivo_consulta_nuevo = True
            elif cv_actual and hasattr(cv_actual, 'motivo_consulta'):
                nueva_cv_data['motivo_consulta'] = cv_actual.motivo_consulta
            
            if enfermedad_final is not None:
                nueva_cv_data['enfermedad_actual'] = enfermedad_final
                instance.enfermedad_actual = enfermedad_final
                instance.enfermedad_actual_nueva = True
            elif cv_actual and hasattr(cv_actual, 'enfermedad_actual'):
                nueva_cv_data['enfermedad_actual'] = cv_actual.enfermedad_actual
            
            # Crear y asociar
            nueva_cv = ConstantesVitales(**nueva_cv_data)
            nueva_cv.full_clean()
            nueva_cv.save()
            instance.constantes_vitales = nueva_cv
            instance.constantes_vitales_nuevas = True
        else:
            # Actualizar solo motivo/enfermedad en historial
            if motivo_final is not None:
                instance.motivo_consulta = motivo_final
                instance.motivo_consulta_nuevo = True
            if enfermedad_final is not None:
                instance.enfermedad_actual = enfermedad_final
                instance.enfermedad_actual_nueva = True
        
        # 7. Manejar otros datos anidados
        if antecedentes_personales_data:
            instance.antecedentes_personales = self._update_or_create_nested(
                AntecedentesPersonales,
                instance.antecedentes_personales,
                antecedentes_personales_data,
                {'paciente': instance.paciente},
            )
        
        if antecedentes_familiares_data:
            instance.antecedentes_familiares = self._update_or_create_nested(
                AntecedentesFamiliares,
                instance.antecedentes_familiares,
                antecedentes_familiares_data,
                {'paciente': instance.paciente},
            )
        
        if examen_estomatognatico_data:
            instance.examen_estomatognatico = self._update_or_create_nested(
                ExamenEstomatognatico,
                instance.examen_estomatognatico,
                examen_estomatognatico_data,
                {'paciente': instance.paciente},
            )
        nuevo_plan = validated_data.get('plan_tratamiento')
        if 'plan_tratamiento' in validated_data:
            if nuevo_plan is not None:
                # Validar que el plan pertenezca al mismo paciente
                if nuevo_plan.paciente_id != instance.paciente_id:
                    raise serializers.ValidationError({
                        'plan_tratamiento': 'El plan de tratamiento debe pertenecer al mismo paciente'
                    })
                
                # Validar que el plan esté activo
                if not nuevo_plan.activo:
                    raise serializers.ValidationError({
                        'plan_tratamiento': 'No se puede asociar un plan inactivo'
                    })
        
        # 8. Actualizar campos directos
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # 9. Guardar
        instance.save()
        
        logger.info(
            f"Historial {instance.id} actualizado. "
            f"Motivo: {motivo_final is not None}, "
            f"Enfermedad: {enfermedad_final is not None}"
        )
        
        return instance
    
    def _update_or_create_nested(self, model_class, current_instance, data, defaults):
        """Helper para actualizar o crear instancias anidadas"""
        if not data:
            return current_instance
        
        nested_id = data.pop('id', None)
        
        if nested_id:
            try:
                nested_obj = model_class.objects.get(id=nested_id)
                for attr, value in data.items():
                    setattr(nested_obj, attr, value)
                nested_obj.save()
                return nested_obj
            except model_class.DoesNotExist:
                pass
        
        if current_instance:
            for attr, value in data.items():
                setattr(current_instance, attr, value)
            current_instance.save()
            return current_instance
        
        data.update(defaults)
        return model_class.objects.create(**data)
    
    def to_representation(self, instance):
        """
        Personalizar la representación del historial con todas las secciones
        """
        data = super().to_representation(instance)
        
        # 1. Formatear fechas
        date_fields = [
            'fecha_atencion',
            'fecha_cierre',
            'fecha_creacion',
            'fecha_modificacion',
        ]
        for field in date_fields:
            val = getattr(instance, field, None)
            if val:
                data[field] = val.isoformat()
                print(f" Fecha {field}: {data[field]}")
        
        # 2. Constantes vitales
        if instance.constantes_vitales:
            cv_serializer = WritableConstantesVitalesSerializer(
                instance.constantes_vitales
            )
            data['constantes_vitales_data'] = cv_serializer.data
            if instance.constantes_vitales.fecha_consulta:
                data['constantes_vitales_data']['fecha_consulta'] = (
                    instance.constantes_vitales.fecha_consulta.isoformat()
                )
        
        # 3.  INDICADORES DE SALUD BUCAL - USAR FK PRIMERO
        print(f" Verificando indicadores para historial {instance.id}")
        
        if instance.indicadores_salud_bucal:
            
            data['indicadores_salud_bucal_data'] = OralHealthIndicatorsSerializer(
                instance.indicadores_salud_bucal
            ).data
            
        else:
            from api.clinical_records.services.indicadores_service import ClinicalRecordIndicadoresService
            
            indicadores_latest = ClinicalRecordIndicadoresService.obtener_indicadores_paciente(
                str(instance.paciente_id)
            )
            
            if indicadores_latest:
                data['indicadores_salud_bucal_data'] = OralHealthIndicatorsSerializer(
                    indicadores_latest
                ).data
                print(f" Indicadores más recientes del paciente encontrados:")
                print(f"   - ID: {indicadores_latest.id}")
                print(f"   - Fecha: {indicadores_latest.fecha}")
            else:
                data['indicadores_salud_bucal_data'] = None
                print(f" No hay indicadores para este paciente")
        
        # 4. Antecedentes personales
        if instance.antecedentes_personales:
            ap_serializer = WritableAntecedentesPersonalesSerializer(
                instance.antecedentes_personales
            )
            data['antecedentes_personales_data'] = ap_serializer.data
            print(f" Antecedentes personales agregados")
        
        # 5. Antecedentes familiares
        if instance.antecedentes_familiares:
            af_serializer = WritableAntecedentesFamiliaresSerializer(
                instance.antecedentes_familiares
            )
            data['antecedentes_familiares_data'] = af_serializer.data
            print(f" Antecedentes familiares agregados")
        
        # 6. Examen estomatognático
        if instance.examen_estomatognatico:
            ee_serializer = WritableExamenEstomatognaticoSerializer(
                instance.examen_estomatognatico
            )
            data['examen_estomatognatico_data'] = ee_serializer.data
            # print(f" Examen estomatognático agregado")
            
        diagnosticos_cie = DiagnosticosCIEService.obtener_diagnosticos_historial(str(instance.id))
        if diagnosticos_cie:
            data['diagnosticos_cie_data'] = {
                'diagnosticos': diagnosticos_cie,
                'tipo_carga': instance.tipo_carga_diagnosticos or 'nuevos'
            }
            print(f" Diagnósticos CIE agregados: {len(diagnosticos_cie)}")
        else:
            data['diagnosticos_cie_data'] = None
            
        
            
        diagnosticos_cie = DiagnosticosCIEService.obtener_diagnosticos_historial(str(instance.id))
        if diagnosticos_cie:
            # Filtrar solo activos
            diagnosticos_activos = [d for d in diagnosticos_cie if d.get('activo', True)]
            
            data['diagnosticos_cie_data'] = {
                'diagnosticos': diagnosticos_activos,
                'tipo_carga': instance.tipo_carga_diagnosticos or 'nuevos',
                'total': len(diagnosticos_activos),
                'total_inactivos': len(diagnosticos_cie) - len(diagnosticos_activos)
            }
            print(f" Diagnósticos CIE activos: {len(diagnosticos_activos)}")
        else:
            data['diagnosticos_cie_data'] = None
        
        # 7. CAMPOS INSTITUCIONALES
        data['institucion_sistema'] = instance.institucion_sistema or "SISTEMA NACIONAL DE SALUD"
        data['unicodigo'] = instance.unicodigo or ""
        data['establecimiento_salud'] = instance.establecimiento_salud or ""
        data['numero_hoja'] = instance.numero_hoja or 1
        data['numero_historia_clinica_unica'] = instance.numero_historia_clinica_unica or ""
        data['numero_archivo'] = instance.numero_archivo or ""
        
        
        return data


class ClinicalRecordCreateSerializer(serializers.ModelSerializer):
    """Serializer para creación de historiales clínicos"""
    
    numero_hoja = serializers.IntegerField(read_only=True)
    
    # Campos editables
    temperatura = serializers.DecimalField(
        max_digits=4, 
        decimal_places=1, 
        required=False, 
        allow_null=True
    )
    pulso = serializers.IntegerField(required=False, allow_null=True)
    frecuencia_respiratoria = serializers.IntegerField(
        required=False, 
        allow_null=True
    )
    presion_arterial = serializers.CharField(required=False, allow_blank=True)
    
    institucion_sistema = serializers.CharField(
        required=False,
        default=INSTITUCION_CONFIG['INSTITUCION_SISTEMA'],
        help_text='Institución del sistema de salud'
    )
    
    establecimiento_salud = serializers.CharField(
        required=False,
        default=INSTITUCION_CONFIG['ESTABLECIMIENTO_SALUD'],
        allow_blank=True,
        help_text='Nombre del establecimiento de salud'
    )
    
    unicodigo = serializers.CharField(
        max_length=50,
        required=False,  
        default=INSTITUCION_CONFIG['UNICODIGO_DEFAULT'],
        allow_null=True,
        allow_blank=True,
        help_text="Código institucional asignado manualmente"
    )
    
    diagnosticos_cie = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True,
        help_text="Lista de diagnósticos CIE a guardar automáticamente"
    )
    
    tipo_carga_diagnosticos = serializers.ChoiceField(
        choices=[
            ('nuevos', 'Solo nuevos diagnósticos'),
            ('todos', 'Todos los diagnósticos'),
        ],
        required=False,
        default='nuevos',
        help_text="Tipo de carga de diagnósticos"
    )
    
    numero_hoja = serializers.IntegerField(read_only=True)
    numero_historia_clinica_unica = serializers.CharField(read_only=True)
    numero_archivo = serializers.CharField(read_only=True)
    
    class Meta:
        model = ClinicalRecord
        fields = [
            'paciente',
            'odontologo_responsable',
            'temperatura',
            'pulso',
            'frecuencia_respiratoria',
            'presion_arterial',
            'motivo_consulta',
            'embarazada',
            'enfermedad_actual',
            'antecedentes_personales',
            'antecedentes_familiares',
            'constantes_vitales',
            'examen_estomatognatico',
            'estado',
            'observaciones',
            
            # Nuevos campos agregados
            'institucion_sistema',
            'establecimiento_salud',
            'unicodigo',
            'numero_hoja',
            'numero_historia_clinica_unica',
            'numero_archivo',
                        'diagnosticos_cie',
            'tipo_carga_diagnosticos',
            'plan_tratamiento',

            
        ]
        extra_kwargs = {
            'institucion_sistema': {
                'required': False,
                'default': 'SISTEMA NACIONAL DE SALUD',
            },
            'unicodigo': {'required': False, 'allow_blank': True},
            'numero_hoja': {'required': False, 'read_only': True},
            'numero_historia_clinica_unica': {'read_only': True},
            'numero_archivo': {'read_only': True},
            'institucion_sistema': {'required': False},
            'establecimiento_salud': {'required': False, 'allow_blank': True},
            'motivo_consulta': {'required': False, 'allow_blank': True},
            'enfermedad_actual': {'required': False, 'allow_blank': True},
            'diagnosticos_cie': {'required': False, 'write_only': True},
            'tipo_carga_diagnosticos': {'required': False},
            'plan_tratamiento': {'required': False, 'allow_null': True},
        }
    
    def validate_paciente(self, value):
        if not value.activo:
            raise serializers.ValidationError(
                'No se puede crear un historial para un paciente inactivo.'
            )
        return value
    
    def validate_odontologo_responsable(self, value):
        if value.rol != 'Odontologo':
            raise serializers.ValidationError(
                'El responsable debe ser un odontólogo.'
            )
        return value
    
    def validate(self, attrs):
        paciente = attrs.get('paciente')
        embarazada = attrs.get('embarazada')
        
        if embarazada == 'SI' and paciente.sexo == 'M':
            raise serializers.ValidationError(
                {'embarazada': 'Un paciente masculino no puede estar embarazado.'}
            )
        return attrs


class ClinicalRecordCloseSerializer(serializers.Serializer):
    """Serializer para cerrar historiales clínicos"""
    
    observaciones_cierre = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text='Observaciones finales antes del cierre',
    )


class ClinicalRecordReopenSerializer(serializers.Serializer):
    """Serializer para reabrir historiales clínicos"""
    
    motivo_reapertura = serializers.CharField(
        required=True, 
        help_text='Motivo de la reapertura del historial'
    )
    

