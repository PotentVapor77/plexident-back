# src/api/clinical_records/serializers/clinical_record.py

"""
Serializers principales para Clinical Record
"""
from jsonschema import ValidationError
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
from api.clinical_records.services.vital_signs_service import VitalSignsService
from api.clinical_records.serializers.examenes_complementarios import ExamenesComplementariosResumenSerializer, WritableExamenesComplementariosSerializer
from api.clinical_records.serializers import examenes_complementarios

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
                
        
        if examenes_complementarios:
            data['examenes_complementarios_data'] = WritableExamenesComplementariosSerializer(
                examenes_complementarios
            ).data

        
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
    
    examenes_complementarios_data = ExamenesComplementariosResumenSerializer(
        source='examenes_complementarios',
        read_only=True,
        allow_null=True,
    )
    
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
            'examenes_complementarios_data',
        )
    
    def update(self, instance, validated_data):
        """
        Actualiza un historial clínico existente.
        Maneja actualización de relaciones anidadas.
        """
        from api.patients.models.antecedentes_personales import AntecedentesPersonales
        from api.patients.models.antecedentes_familiares import AntecedentesFamiliares
        from api.patients.models.constantes_vitales import ConstantesVitales
        from api.patients.models.examen_estomatognatico import ExamenEstomatognatico
        from api.odontogram.models import IndiceCariesSnapshot
        
        usuario = self.context['request'].user
        paciente = instance.paciente
        
        # ============================================================================
        # CORRECCIÓN: Verificar el tipo de dato antes de procesar
        # ============================================================================
        
        # ANTECEDENTES PERSONALES
        if 'antecedentes_personales' in validated_data:
            ap_data = validated_data.pop('antecedentes_personales')
            instance.antecedentes_personales = self._update_or_create_nested(
                AntecedentesPersonales,
                WritableAntecedentesPersonalesSerializer,
                ap_data,
                paciente,
                usuario
            )
        
        # ANTECEDENTES FAMILIARES
        if 'antecedentes_familiares' in validated_data:
            af_data = validated_data.pop('antecedentes_familiares')
            instance.antecedentes_familiares = self._update_or_create_nested(
                AntecedentesFamiliares,
                WritableAntecedentesFamiliaresSerializer,
                af_data,
                paciente,
                usuario
            )
        
        # CONSTANTES VITALES
        if 'constantes_vitales' in validated_data:
            cv_data = validated_data.pop('constantes_vitales')
            
            # Manejar constantes vitales (puede ser nueva o actualización)
            if VitalSignsService.tiene_datos_vitales({'constantes_vitales': cv_data}):
                nueva_constante = VitalSignsService.crear_constantes_vitales(
                    paciente=paciente,
                    data={'constantes_vitales': cv_data},
                    creado_por=usuario
                )
                instance.constantes_vitales = nueva_constante
                instance.constantes_vitales_nuevas = True
            else:
                # Actualizar constante existente si se proporciona ID
                instance.constantes_vitales = self._update_or_create_nested(
                    ConstantesVitales,
                    WritableConstantesVitalesSerializer,
                    cv_data,
                    paciente,
                    usuario
                )
        
        # EXAMEN ESTOMATOGNÁTICO (Línea 428 del error original)
        if 'examen_estomatognatico' in validated_data:
            ee_data = validated_data.pop('examen_estomatognatico')
            instance.examen_estomatognatico = self._update_or_create_nested(
                ExamenEstomatognatico,
                WritableExamenEstomatognaticoSerializer,
                ee_data,  # Ahora se maneja correctamente si es dict o instancia
                paciente,
                usuario
            )

        
        # ÍNDICES DE CARIES
        if 'indices_caries' in validated_data:
            ic_data = validated_data.pop('indices_caries')
            instance.indices_caries = self._update_or_create_nested(
                IndiceCariesSnapshot,
                WritableIndicesCariesSerializer,
                ic_data,
                paciente,
                usuario
            )
        
        # MOTIVO CONSULTA Y ENFERMEDAD ACTUAL
        if 'motivo_consulta' in validated_data:
            instance.motivo_consulta = validated_data.pop('motivo_consulta')
            instance.motivo_consulta_nuevo = True
        
        if 'enfermedad_actual' in validated_data:
            instance.enfermedad_actual = validated_data.pop('enfermedad_actual')
            instance.enfermedad_actual_nueva = True
        
        # Actualizar campos restantes
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Actualizar metadata
        instance.actualizado_por = usuario
        
        # Guardar
        instance.save()
        
        return instance
    
    def _update_or_create_nested(self, related_model, serializer_class, data, paciente, usuario):
        """
        Crea o actualiza un objeto relacionado (nested).
        
        Args:
            related_model: Clase del modelo relacionado
            serializer_class: Clase del serializer a usar
            data: Diccionario con datos O instancia ya deserializada
            paciente: Instancia de Paciente
            usuario: Usuario que realiza la operación
        
        Returns:
            Instancia del modelo relacionado
        """
        # ============================================================================
        # CORRECCIÓN DEL BUG: Verificar si data ya es una instancia del modelo
        # ============================================================================
        
        # Si data ya es una instancia del modelo (ya fue deserializado por el serializer),
        # simplemente retornarlo
        if isinstance(data, related_model):
            return data
        
        # Si data no es un diccionario, convertirlo (por si es OrderedDict u otro tipo)
        if not isinstance(data, dict):
            try:
                data = dict(data)
            except (TypeError, ValueError):
                # Si no se puede convertir a dict, asumir que es una instancia
                if hasattr(data, 'id'):
                    return data
                raise ValidationError(
                    f"Datos inválidos para {related_model.__name__}: "
                    f"se esperaba un diccionario o instancia, se recibió {type(data)}"
                )
        
        # ============================================================================
        # Ahora sí, data es un diccionario y podemos procesarlo
        # ============================================================================
        
        # Extraer el ID si existe (sin mutar el diccionario original)
        nested_id = data.get('id', None)
        
        # Caso 1: Tiene ID - Actualizar existente
        if nested_id:
            try:
                instance = related_model.objects.get(id=nested_id, activo=True)
                
                # Crear una copia del diccionario para no mutar el original
                data_copy = data.copy()
                data_copy.pop('id', None)  # Remover ID de la copia
                
                # Actualizar con el serializer
                serializer = serializer_class(
                    instance,
                    data=data_copy,
                    partial=True,
                    context=self.context
                )
                serializer.is_valid(raise_exception=True)
                return serializer.save(actualizado_por=usuario)
                
            except related_model.DoesNotExist:
                # Si el ID no existe, crear uno nuevo
                logger.warning(
                    f"ID {nested_id} para {related_model.__name__} no encontrado. "
                    f"Creando nuevo registro."
                )
                # Continuar al caso 2 (crear nuevo)
                nested_id = None
        
        # Caso 2: No tiene ID o el ID no existe - Crear nuevo
        if not nested_id:
            # Verificar si ya existe uno para este paciente (relación OneToOne)
            try:
                instance = related_model.objects.get(paciente=paciente, activo=True)
                
                # Ya existe, actualizarlo
                data_copy = data.copy()
                data_copy.pop('id', None)
                
                serializer = serializer_class(
                    instance,
                    data=data_copy,
                    partial=True,
                    context=self.context
                )
                serializer.is_valid(raise_exception=True)
                return serializer.save(actualizado_por=usuario)
                
            except related_model.DoesNotExist:
                # No existe, crear uno nuevo
                data_copy = data.copy()
                data_copy.pop('id', None)
                data_copy['paciente'] = paciente.id
                
                serializer = serializer_class(
                    data=data_copy,
                    context=self.context
                )
                serializer.is_valid(raise_exception=True)
                return serializer.save(creado_por=usuario)

    
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
        if instance.examenes_complementarios:
            data['examenes_complementarios_data'] = (
                WritableExamenesComplementariosSerializer(
                    instance.examenes_complementarios
                ).data
            )
            print(f"✓ Exámenes complementarios incluidos: {instance.examenes_complementarios.id}")
        else:
            data['examenes_complementarios_data'] = None
            print(f"✗ No hay exámenes complementarios para historial {instance.id}")
        
        
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
    

