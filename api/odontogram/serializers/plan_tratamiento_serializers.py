from rest_framework import serializers
from api.odontogram.models import PlanTratamiento, SesionTratamiento, Paciente
from django.contrib.auth import get_user_model

User = get_user_model()


class SesionTratamientoListSerializer(serializers.ModelSerializer):
    """Serializer para listado de sesiones"""
    odontologo_nombre = serializers.SerializerMethodField()
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    esta_firmada = serializers.SerializerMethodField()
    total_diagnosticos = serializers.SerializerMethodField()
    total_procedimientos = serializers.SerializerMethodField()
    total_prescripciones = serializers.SerializerMethodField()
    
    class Meta:
        model = SesionTratamiento
        fields = [
            'id', 'numero_sesion', 'fecha_programada', 'fecha_realizacion',
            'estado', 'estado_display', 'esta_firmada', 'odontologo_nombre',
            'total_diagnosticos', 'total_procedimientos', 'total_prescripciones',
            'fecha_firma', 'fecha_creacion'
        ]
    
    def get_odontologo_nombre(self, obj):
        if obj.odontologo:
            return f"{obj.odontologo.nombres} {obj.odontologo.apellidos}"
        return None
    
    def get_esta_firmada(self, obj):
        return bool(obj.firma_digital and obj.fecha_firma)
    
    def get_total_diagnosticos(self, obj):
        return len(obj.diagnosticos_complicaciones) if obj.diagnosticos_complicaciones else 0
    
    def get_total_procedimientos(self, obj):
        return len(obj.procedimientos) if obj.procedimientos else 0
    
    def get_total_prescripciones(self, obj):
        return len(obj.prescripciones) if obj.prescripciones else 0


class SesionTratamientoDetailSerializer(serializers.ModelSerializer):
    """Serializer detallado para una sesión"""
    odontologo_info = serializers.SerializerMethodField()
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    
    class Meta:
        model = SesionTratamiento
        fields = [
            'id', 'numero_sesion', 'fecha_programada', 'fecha_realizacion',
            'estado', 'estado_display', 'diagnosticos_complicaciones',
            'procedimientos', 'prescripciones', 'notas', 'observaciones',
            'odontologo_info', 'firma_digital', 'fecha_firma',
            'fecha_creacion', 'fecha_actualizacion', 'activo'
        ]
        read_only_fields = ['id', 'numero_sesion', 'fecha_creacion', 'fecha_actualizacion']
    
    def get_odontologo_info(self, obj):
        if obj.odontologo:
            return {
                'id': obj.odontologo.id,
                'nombres': obj.odontologo.nombres,
                'apellidos': obj.odontologo.apellidos,
                'correo': obj.odontologo.correo
            }
        return None


class SesionTratamientoCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear/actualizar sesiones"""
    autocompletar_diagnosticos = serializers.BooleanField(
        default=True, 
        write_only=True,
        help_text="Si es True, autocompleta diagnósticos del último odontograma"
    )
    
    class Meta:
        model = SesionTratamiento
        fields = [
            'plan_tratamiento', 'fecha_programada', 'diagnosticos_complicaciones',
            'procedimientos', 'prescripciones', 'notas', 'observaciones',
            'autocompletar_diagnosticos', 'estado'
        ]
    
    def validate(self, data):
        plan = data.get('plan_tratamiento')
        if plan:
            # Obtener el siguiente número de sesión
            ultima_sesion = SesionTratamiento.objects.filter(
                plan_tratamiento=plan
            ).order_by('-numero_sesion').first()
            
            data['numero_sesion'] = (ultima_sesion.numero_sesion + 1) if ultima_sesion else 1
        
        return data


class PlanTratamientoListSerializer(serializers.ModelSerializer):
    """Serializer para listado de planes"""
    paciente_nombre = serializers.CharField(
        source='paciente.get_full_name', 
        read_only=True
    )
    creado_por_nombre = serializers.SerializerMethodField()
    total_sesiones = serializers.SerializerMethodField()
    sesiones_completadas = serializers.SerializerMethodField()
    
    class Meta:
        model = PlanTratamiento
        fields = [
            'id', 'titulo', 'paciente_nombre', 'fecha_creacion',
            'creado_por_nombre', 'total_sesiones', 'sesiones_completadas',
            'activo', 'version_odontograma'
        ]
    
    def get_creado_por_nombre(self, obj):
        if obj.creado_por:
            return f"{obj.creado_por.nombres} {obj.creado_por.apellidos}"
        return None
    
    def get_total_sesiones(self, obj):
        return obj.sesiones.filter(activo=True).count()
    
    def get_sesiones_completadas(self, obj):
        return obj.sesiones.filter(
            activo=True, 
            estado=SesionTratamiento.EstadoSesion.COMPLETADA
        ).count()


class PlanTratamientoDetailSerializer(serializers.ModelSerializer):
    """Serializer detallado del plan de tratamiento con sesiones"""
    paciente_info = serializers.SerializerMethodField()
    creado_por_info = serializers.SerializerMethodField()
    sesiones = SesionTratamientoListSerializer(many=True, read_only=True)
    estadisticas = serializers.SerializerMethodField()
    
    class Meta:
        model = PlanTratamiento
        fields = [
            'id', 'titulo', 'paciente_info', 'fecha_creacion', 'fecha_actualizacion',
            'creado_por_info', 'notas_generales', 'version_odontograma',
            'sesiones', 'estadisticas', 'activo'
        ]
        read_only_fields = ['id', 'fecha_creacion', 'fecha_actualizacion']
    
    def get_paciente_info(self, obj):
        return {
            'id': str(obj.paciente.id),
            'nombres': obj.paciente.nombres,
            'apellidos': obj.paciente.apellidos,
            'cedula_pasaporte': obj.paciente.cedula_pasaporte
        }
    
    def get_creado_por_info(self, obj):
        if obj.creado_por:
            return {
                'id': obj.creado_por.id,
                'nombres': obj.creado_por.nombres,
                'apellidos': obj.creado_por.apellidos
            }
        return None
    
    def get_estadisticas(self, obj):
        sesiones = obj.sesiones.filter(activo=True)
        return {
            'total': sesiones.count(),
            'planificadas': sesiones.filter(estado='planificada').count(),
            'en_progreso': sesiones.filter(estado='en_progreso').count(),
            'completadas': sesiones.filter(estado='completada').count(),
            'canceladas': sesiones.filter(estado='cancelada').count(),
        }


class PlanTratamientoCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear plan de tratamiento"""
    usar_ultimo_odontograma = serializers.BooleanField(
        default=True,
        write_only=True,
        help_text="Si es True, usa el último odontograma guardado del paciente"
    )
    
    class Meta:
        model = PlanTratamiento
        fields = [
            'paciente', 'titulo', 'notas_generales', 
            'usar_ultimo_odontograma', 'version_odontograma'
        ]
    
    def validate(self, data):
        if data.get('usar_ultimo_odontograma') and not data.get('version_odontograma'):
            # Se manejará en el service para obtener el último version_id
            pass
        return data
