from rest_framework import serializers
from api.clinical_records.models import ClinicalRecord
from api.patients.models.paciente import Paciente
from api.patients.models.antecedentes_personales import AntecedentesPersonales
from api.patients.models.antecedentes_familiares import AntecedentesFamiliares
from api.patients.models.constantes_vitales import ConstantesVitales
from api.patients.models.examen_estomatognatico import ExamenEstomatognatico
from api.patients.serializers import (
    PacienteSerializer,
    AntecedentesPersonalesSerializer,
    AntecedentesFamiliaresSerializer,
    ConstantesVitalesSerializer,
    ExamenEstomatognaticoSerializer
)
from api.users.models import Usuario


# ===== WRITABLE NESTED SERIALIZERS =====
class WritableAntecedentesPersonalesSerializer(AntecedentesPersonalesSerializer):
    """Serializer writable para antecedentes personales anidados"""
    id = serializers.UUIDField(required=False)
    
    class Meta(AntecedentesPersonalesSerializer.Meta):
        read_only_fields = ('fecha_creacion', 'fecha_modificacion', 'creado_por', 'actualizado_por')


class WritableAntecedentesFamiliaresSerializer(AntecedentesFamiliaresSerializer):
    """Serializer writable para antecedentes familiares anidados"""
    id = serializers.UUIDField(required=False)
    
    class Meta(AntecedentesFamiliaresSerializer.Meta):
        read_only_fields = ('fecha_creacion', 'fecha_modificacion', 'creado_por', 'actualizado_por')


class WritableConstantesVitalesSerializer(ConstantesVitalesSerializer):
    """Serializer writable para constantes vitales anidadas"""
    id = serializers.UUIDField(required=False)
    
    class Meta(ConstantesVitalesSerializer.Meta):
        read_only_fields = ('fecha_creacion', 'fecha_modificacion', 'creado_por', 'actualizado_por')


class WritableExamenEstomatognaticoSerializer(ExamenEstomatognaticoSerializer):
    """Serializer writable para examen estomatognático anidado"""
    id = serializers.UUIDField(required=False)
    
    class Meta(ExamenEstomatognaticoSerializer.Meta):
        read_only_fields = ('fecha_creacion', 'fecha_modificacion', 'creado_por', 'actualizado_por')


# ===== SERIALIZERS PRINCIPALES (mantener los existentes) =====
class ClinicalRecordSerializer(serializers.ModelSerializer):
    """Mantener como está"""
    paciente_nombre = serializers.CharField(source='paciente.nombre_completo', read_only=True)
    paciente_cedula = serializers.CharField(source='paciente.cedula_pasaporte', read_only=True)
    odontologo_nombre = serializers.CharField(source='odontologo_responsable.get_full_name', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    puede_editar = serializers.BooleanField(read_only=True)
    esta_completo = serializers.BooleanField(read_only=True)

    class Meta:
        model = ClinicalRecord
        fields = [
            'id', 'paciente', 'paciente_nombre', 'paciente_cedula',
            'odontologo_responsable', 'odontologo_nombre',
            'fecha_atencion', 'fecha_creacion', 'fecha_cierre',
            'estado', 'estado_display', 'motivo_consulta',
            'activo', 'puede_editar', 'esta_completo'
        ]
        read_only_fields = (
            'id', 'creado_por', 'actualizado_por',
            'fecha_creacion', 'fecha_modificacion',
            'fecha_atencion', 'fecha_cierre'
        )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data.get('fecha_atencion'):
            data['fecha_atencion'] = instance.fecha_atencion.isoformat()
        if data.get('fecha_cierre') and instance.fecha_cierre:
            data['fecha_cierre'] = instance.fecha_cierre.isoformat()
        if data.get('fecha_creacion'):
            data['fecha_creacion'] = instance.fecha_creacion.isoformat()
        if data.get('fecha_modificacion') and instance.fecha_modificacion:
            data['fecha_modificacion'] = instance.fecha_modificacion.isoformat()
        return data


class ClinicalRecordDetailSerializer(serializers.ModelSerializer):
    """Serializer detallado - AHORA CON NESTED WRITABLE"""
    
    # Información expandida del paciente (read only)
    paciente_info = serializers.SerializerMethodField()
    odontologo_info = serializers.SerializerMethodField()
    creado_por_info = serializers.SerializerMethodField()
    
    # Secciones expandidas - AHORA WRITABLE
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
        allow_null=True
    )
    examen_estomatognatico_data = WritableExamenEstomatognaticoSerializer(
        source='examen_estomatognatico',
        required=False,
        allow_null=True
    )
    
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    puede_editar = serializers.BooleanField(read_only=True)
    esta_completo = serializers.BooleanField(read_only=True)

    class Meta:
        model = ClinicalRecord
        fields = '__all__'
        read_only_fields = (
            'id', 'creado_por', 'actualizado_por',
            'fecha_creacion', 'fecha_modificacion',
            'fecha_atencion', 'fecha_cierre', 'paciente'
        )

    def get_paciente_info(self, obj):
        if not obj.paciente:
            return None
        return {
            'id': str(obj.paciente.id),
            'nombres': obj.paciente.nombres,
            'apellidos': obj.paciente.apellidos,
            'cedula_pasaporte': obj.paciente.cedula_pasaporte,
            'sexo': obj.paciente.sexo,
            'edad': obj.paciente.edad,
            'fecha_nacimiento': obj.paciente.fecha_nacimiento.isoformat() if obj.paciente.fecha_nacimiento else None,
        }

    def get_odontologo_info(self, obj):
        if not obj.odontologo_responsable:
            return None
        return {
            'id': str(obj.odontologo_responsable.id),
            'nombres': obj.odontologo_responsable.nombres,
            'apellidos': obj.odontologo_responsable.apellidos,
            'rol': obj.odontologo_responsable.rol,
        }

    def get_creado_por_info(self, obj):
        if not obj.creado_por:
            return None
        return {
            'nombres': obj.creado_por.nombres,
            'apellidos': obj.creado_por.apellidos,
        }

    def update(self, instance, validated_data):
        """Manejar actualizaciones de secciones anidadas"""
        
        # Extraer datos anidados
        antecedentes_personales_data = validated_data.pop('antecedentes_personales', None)
        antecedentes_familiares_data = validated_data.pop('antecedentes_familiares', None)
        constantes_vitales_data = validated_data.pop('constantes_vitales', None)
        examen_estomatognatico_data = validated_data.pop('examen_estomatognatico', None)
        
        # Actualizar campos directos del Clinical Record
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Actualizar o crear Antecedentes Personales
        if antecedentes_personales_data is not None:
            instance.antecedentes_personales = self._update_or_create_nested(
                AntecedentesPersonales,
                instance.antecedentes_personales,
                antecedentes_personales_data,
                {'paciente': instance.paciente}
            )
        
        # Actualizar o crear Antecedentes Familiares
        if antecedentes_familiares_data is not None:
            instance.antecedentes_familiares = self._update_or_create_nested(
                AntecedentesFamiliares,
                instance.antecedentes_familiares,
                antecedentes_familiares_data,
                {'paciente': instance.paciente}
            )
        
        # Actualizar o crear Constantes Vitales
        if constantes_vitales_data is not None:
            instance.constantes_vitales = self._update_or_create_nested(
                ConstantesVitales,
                instance.constantes_vitales,
                constantes_vitales_data,
                {'paciente': instance.paciente}
            )
        
        # Actualizar o crear Examen Estomatognático
        if examen_estomatognatico_data is not None:
            instance.examen_estomatognatico = self._update_or_create_nested(
                ExamenEstomatognatico,
                instance.examen_estomatognatico,
                examen_estomatognatico_data,
                {'paciente': instance.paciente}
            )
        
        instance.save()
        return instance

    def _update_or_create_nested(self, model_class, current_instance, data, defaults):
        """
        Helper para actualizar o crear instancias anidadas
        
        Args:
            model_class: Modelo a actualizar/crear
            current_instance: Instancia actual (puede ser None)
            data: Datos validados del serializer
            defaults: Campos default (como paciente)
        """
        if not data:
            return current_instance
        
        nested_id = data.pop('id', None)
        
        # Si viene un ID y existe, actualizar esa instancia
        if nested_id:
            try:
                nested_obj = model_class.objects.get(id=nested_id)
                for attr, value in data.items():
                    setattr(nested_obj, attr, value)
                nested_obj.save()
                return nested_obj
            except model_class.DoesNotExist:
                pass
        
        # Si existe una instancia actual y no viene ID, actualizar la actual
        if current_instance:
            for attr, value in data.items():
                setattr(current_instance, attr, value)
            current_instance.save()
            return current_instance
        
        # Si no existe, crear nueva
        data.update(defaults)
        return model_class.objects.create(**data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data.get('fecha_atencion'):
            data['fecha_atencion'] = instance.fecha_atencion.isoformat()
        if data.get('fecha_cierre') and instance.fecha_cierre:
            data['fecha_cierre'] = instance.fecha_cierre.isoformat()
        if data.get('fecha_creacion'):
            data['fecha_creacion'] = instance.fecha_creacion.isoformat()
        if data.get('fecha_modificacion') and instance.fecha_modificacion:
            data['fecha_modificacion'] = instance.fecha_modificacion.isoformat()
        return data


class ClinicalRecordCreateSerializer(serializers.ModelSerializer):
    """Mantener como está para creación simple"""
    class Meta:
        model = ClinicalRecord
        fields = [
            'paciente', 'odontologo_responsable',
            'motivo_consulta', 'embarazada', 'enfermedad_actual',
            'antecedentes_personales', 'antecedentes_familiares',
            'constantes_vitales', 'examen_estomatognatico',
            'estado', 'observaciones', 'unicodigo', 'establecimiento_salud',
        ]

    def validate_paciente(self, value):
        if not value.activo:
            raise serializers.ValidationError('No se puede crear un historial para un paciente inactivo.')
        return value

    def validate_odontologo_responsable(self, value):
        if value.rol != 'Odontologo':
            raise serializers.ValidationError('El responsable debe ser un odontólogo.')
        return value

    def validate(self, attrs):
        paciente = attrs.get('paciente')
        embarazada = attrs.get('embarazada')
        if embarazada == 'SI' and paciente.sexo == 'M':
            raise serializers.ValidationError({
                'embarazada': 'Un paciente masculino no puede estar embarazado.'
            })
        return attrs


class ClinicalRecordUpdateSerializer(serializers.ModelSerializer):
    """
    NUEVO: Serializer simplificado para actualizaciones.
    Para edición completa con nested data, usar ClinicalRecordDetailSerializer.
    """
    
    # Permitir actualizar solo IDs (comportamiento actual)
    # Para nested updates, el frontend debe usar el endpoint con DetailSerializer
    
    class Meta:
        model = ClinicalRecord
        fields = [
            'motivo_consulta', 'embarazada', 'enfermedad_actual',
            'antecedentes_personales', 'antecedentes_familiares',
            'constantes_vitales', 'examen_estomatognatico',
            'estado', 'observaciones',
            'unicodigo', 'establecimiento_salud', 'numero_hoja',
            'institucion_sistema'
        ]

    def validate(self, attrs):
        if self.instance and self.instance.estado == 'CERRADO':
            raise serializers.ValidationError('No se puede editar un historial cerrado.')
        return attrs


class ClinicalRecordCloseSerializer(serializers.Serializer):
    """Mantener como está"""
    observaciones_cierre = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text='Observaciones finales antes del cierre'
    )


class ClinicalRecordReopenSerializer(serializers.Serializer):
    """Mantener como está"""
    motivo_reapertura = serializers.CharField(
        required=True,
        help_text='Motivo de la reapertura del historial'
    )
