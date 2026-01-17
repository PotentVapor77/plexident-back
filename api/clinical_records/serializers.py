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


class ClinicalRecordSerializer(serializers.ModelSerializer):
    paciente_nombre = serializers.CharField(source='paciente.nombre_completo', read_only=True)
    paciente_cedula = serializers.CharField(source='paciente.cedula_pasaporte', read_only=True)
    odontologo_nombre = serializers.CharField(source='odontologo_responsable.get_full_name', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    puede_editar = serializers.BooleanField(read_only=True)
    esta_completo = serializers.BooleanField(read_only=True)

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
            'esta_completo'
        ]
        read_only_fields = (
            'id', 'creado_por', 'actualizado_por',
            'fecha_creacion', 'fecha_modificacion',
            'fecha_atencion', 'fecha_cierre'
        )
    
    def to_representation(self, instance):
        """Formato compatible con frontend"""
        data = super().to_representation(instance)
        
        # Convertir fechas a ISO string
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
    """Serializer detallado con todas las secciones expandidas"""
    
    # Información expandida del paciente
    paciente_info = serializers.SerializerMethodField()
    
    # Información expandida del odontólogo
    odontologo_info = serializers.SerializerMethodField()
    
    # Información de quien creó el registro
    creado_por_info = serializers.SerializerMethodField()
    
    # Secciones expandidas (mantén las que ya tienes)
    antecedentes_personales_data = AntecedentesPersonalesSerializer(
        source='antecedentes_personales', 
        read_only=True
    )
    antecedentes_familiares_data = AntecedentesFamiliaresSerializer(
        source='antecedentes_familiares', 
        read_only=True
    )
    constantes_vitales_data = ConstantesVitalesSerializer(
        source='constantes_vitales', 
        read_only=True
    )
    examen_estomatognatico_data = ExamenEstomatognaticoSerializer(
        source='examen_estomatognatico', 
        read_only=True
    )
    
    # Campos computados
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    
    # Properties
    puede_editar = serializers.BooleanField(read_only=True)
    esta_completo = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = ClinicalRecord
        fields = '__all__'
        read_only_fields = (
            'id', 'creado_por', 'actualizado_por',
            'fecha_creacion', 'fecha_modificacion',
            'fecha_atencion', 'fecha_cierre'
        )
    
    def get_paciente_info(self, obj):
        """Información del paciente en formato esperado por el frontend"""
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
        """Información del odontólogo responsable"""
        if not obj.odontologo_responsable:
            return None
        return {
            'id': str(obj.odontologo_responsable.id),
            'nombres': obj.odontologo_responsable.nombres,
            'apellidos': obj.odontologo_responsable.apellidos,
            'rol': obj.odontologo_responsable.rol,
        }
    
    def get_creado_por_info(self, obj):
        """Información de quién creó el historial"""
        if not obj.creado_por:
            return None
        return {
            'nombres': obj.creado_por.nombres,
            'apellidos': obj.creado_por.apellidos,
        }
    
    def to_representation(self, instance):
        """Formato compatible con frontend"""
        data = super().to_representation(instance)
        
        # Convertir fechas a ISO string
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
    """Serializer para creación de historiales clínicos"""
    
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
            'estado',
            'observaciones',
            'unicodigo',
            'establecimiento_salud',
        ]
    
    def validate_paciente(self, value):
        """Validar que el paciente esté activo"""
        if not value.activo:
            raise serializers.ValidationError('No se puede crear un historial para un paciente inactivo.')
        return value
    
    def validate_odontologo_responsable(self, value):
        """Validar que el responsable sea odontólogo"""
        if value.rol != 'Odontologo':
            raise serializers.ValidationError('El responsable debe ser un odontólogo.')
        return value
    
    def validate(self, attrs):
        """Validaciones a nivel de objeto"""
        # Validar embarazo según sexo
        paciente = attrs.get('paciente')
        embarazada = attrs.get('embarazada')
        
        if embarazada == 'SI' and paciente.sexo == 'M':
            raise serializers.ValidationError({
                'embarazada': 'Un paciente masculino no puede estar embarazado.'
            })
        
        return attrs


class ClinicalRecordUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualización de historiales clínicos"""
    
    class Meta:
        model = ClinicalRecord
        fields = [
            'motivo_consulta',
            'embarazada',
            'enfermedad_actual',
            'antecedentes_personales',
            'antecedentes_familiares',
            'constantes_vitales',
            'examen_estomatognatico',
            'estado',
            'observaciones',
        ]
    
    def validate(self, attrs):
        """No permitir edición si está cerrado"""
        if self.instance and self.instance.estado == 'CERRADO':
            raise serializers.ValidationError('No se puede editar un historial cerrado.')
        return attrs


class ClinicalRecordCloseSerializer(serializers.Serializer):
    """Serializer para cerrar un historial"""
    
    observaciones_cierre = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text='Observaciones finales antes del cierre'
    )


class ClinicalRecordReopenSerializer(serializers.Serializer):
    """Serializer para reabrir un historial cerrado"""
    
    motivo_reapertura = serializers.CharField(
        required=True,
        help_text='Motivo de la reapertura del historial'
    )
