# api/appointment/serializers.py

from rest_framework import serializers
from .models import Cita, HorarioAtencion, RecordatorioCita, EstadoCita, TipoConsulta
from api.patients.models.paciente import Paciente
from api.users.models import Usuario
from django.utils import timezone
from datetime import datetime, timedelta

class PacienteBasicoSerializer(serializers.ModelSerializer):
    """Serializer simplificado para paciente"""
    nombre_completo = serializers.CharField(read_only=True)
    
    class Meta:
        model = Paciente
        fields = ['id', 'nombres', 'apellidos', 'nombre_completo', 'cedula_pasaporte', 'telefono', 'correo']

class OdontologoBasicoSerializer(serializers.ModelSerializer):
    """Serializer simplificado para odontólogo"""
    nombre_completo = serializers.SerializerMethodField()
    
    class Meta:
        model = Usuario
        fields = ['id', 'nombres', 'apellidos', 'nombre_completo', 'correo']
    
    def get_nombre_completo(self, obj):
        return obj.get_full_name()

# ==================== HORARIO ATENCIÓN ====================

class HorarioAtencionSerializer(serializers.ModelSerializer):
    odontologo_detalle = OdontologoBasicoSerializer(source='odontologo', read_only=True)
    dia_semana_display = serializers.CharField(source='get_dia_semana_display', read_only=True)
    
    class Meta:
        model = HorarioAtencion
        fields = [
            'id', 'odontologo', 'odontologo_detalle', 'dia_semana', 'dia_semana_display',
            'hora_inicio', 'hora_fin', 'duracion_cita', 'activo',
            'fecha_creacion', 'fecha_modificacion'
        ]
        read_only_fields = ['id', 'fecha_creacion', 'fecha_modificacion']
    
    def validate(self, data):
        """
        ✅ CORRECCIÓN: Solo validar si ambos campos están presentes
        Esto permite actualizaciones parciales (PATCH) sin error
        """
        # Obtener valores de la instancia existente si no están en data
        hora_inicio = data.get('hora_inicio')
        hora_fin = data.get('hora_fin')
        
        # Si estamos actualizando (self.instance existe), usar valores existentes como fallback
        if self.instance:
            if hora_inicio is None:
                hora_inicio = self.instance.hora_inicio
            if hora_fin is None:
                hora_fin = self.instance.hora_fin
        
        # Solo validar si tenemos ambos valores
        if hora_inicio and hora_fin:
            if hora_inicio >= hora_fin:
                raise serializers.ValidationError(
                    {"hora_fin": "La hora de fin debe ser mayor que la hora de inicio"}
                )
        
        return data

# ==================== CITAS ====================

class CitaSerializer(serializers.ModelSerializer):
    """Serializer para listado de citas"""
    paciente_detalle = PacienteBasicoSerializer(source='paciente', read_only=True)
    odontologo_detalle = OdontologoBasicoSerializer(source='odontologo', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    tipo_consulta_display = serializers.CharField(source='get_tipo_consulta_display', read_only=True)
    esta_vigente = serializers.BooleanField(read_only=True)
    puede_ser_cancelada = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Cita
        fields = [
            'id', 'paciente', 'paciente_detalle', 'odontologo', 'odontologo_detalle',
            'fecha', 'hora_inicio', 'hora_fin', 'duracion', 'tipo_consulta',
            'tipo_consulta_display', 'estado', 'estado_display', 'motivo_consulta',
            'observaciones', 'esta_vigente', 'puede_ser_cancelada', 'activo',
            'fecha_creacion', 'fecha_modificacion'
        ]
        read_only_fields = ['id', 'fecha_creacion', 'fecha_modificacion']

class CitaDetailSerializer(serializers.ModelSerializer):
    """Serializer detallado para ver una cita"""
    paciente_detalle = PacienteBasicoSerializer(source='paciente', read_only=True)
    odontologo_detalle = OdontologoBasicoSerializer(source='odontologo', read_only=True)
    creado_por_detalle = OdontologoBasicoSerializer(source='creado_por', read_only=True)
    cancelada_por_detalle = OdontologoBasicoSerializer(source='cancelada_por', read_only=True)
    cita_original_detalle = CitaSerializer(source='cita_original', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    tipo_consulta_display = serializers.CharField(source='get_tipo_consulta_display', read_only=True)
    
    class Meta:
        model = Cita
        fields = '__all__'
        read_only_fields = ['id', 'fecha_creacion', 'fecha_modificacion']

class CitaCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear citas"""
    
    class Meta:
        model = Cita
        fields = [
            'paciente', 'odontologo', 'fecha', 'hora_inicio', 'duracion',
            'tipo_consulta', 'motivo_consulta', 'observaciones','estado' 
        ]
        extra_kwargs = {
            'estado': {'required': False}  # ✅ No requerido para crear nuevas citas normales
        }

    def create(self, validated_data):
        # ✅ Si no se especifica estado, usar PROGRAMADA por defecto
        # Pero para reprogramación, el servicio establecerá REPROGRAMADA
        if 'estado' not in validated_data:
            validated_data['estado'] = EstadoCita.PROGRAMADA
        return super().create(validated_data)
    


    def validate_paciente(self, value):
        """Validar que el paciente existe y está activo"""
        if not value.activo:
            raise serializers.ValidationError("El paciente no está activo")
        return value
    
    def validate_odontologo(self, value):
        """Validar que el odontólogo existe y está activo"""
        if not value.is_active:
            raise serializers.ValidationError("El odontólogo no está activo")
        if value.rol != 'Odontologo':
            raise serializers.ValidationError("El usuario no es un odontólogo")
        return value
    
    def validate(self, data):
        """Validaciones generales"""
        fecha_cita = data['fecha']
        hora_cita = data['hora_inicio']
        ahora = timezone.now()
        
        # Solo validar si la fecha es HOY
        if fecha_cita == ahora.date():
            fecha_hora_cita = timezone.make_aware(
                datetime.combine(fecha_cita, hora_cita)
            )
            
            if fecha_hora_cita < (ahora - timedelta(minutes=5)):
                raise serializers.ValidationError(
                    {"hora_inicio": "La hora seleccionada ya pasó"}
                )
        
        # Si la fecha es en el pasado (días anteriores)
        elif fecha_cita < ahora.date():
            raise serializers.ValidationError(
                {"fecha": "No se pueden programar citas en fechas pasadas"}
            )
        
        return data

class CitaUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualizar citas"""
    
    class Meta:
        model = Cita
        fields = [
            'odontologo', 'fecha', 'hora_inicio', 'duracion',
            'tipo_consulta', 'motivo_consulta', 'observaciones', 'estado'
        ]
    
    def validate(self, data):
        """Validar que la cita puede ser actualizada"""
        instance = self.instance
        if instance.estado in [EstadoCita.CANCELADA, EstadoCita.REPROGRAMADA]:
            raise serializers.ValidationError(
                "No se puede modificar una cita cancelada o reprogramada"
            )
        
        # Si se cambia la fecha u hora, validar que no sea en el pasado
        if 'fecha' in data or 'hora_inicio' in data:
            fecha = data.get('fecha', instance.fecha)
            hora_inicio = data.get('hora_inicio', instance.hora_inicio)
            fecha_hora_cita = timezone.make_aware(datetime.combine(fecha, hora_inicio))
            if fecha_hora_cita < timezone.now():
                raise serializers.ValidationError(
                    {"fecha": "No se pueden programar citas en el pasado"}
                )
        
        return data

class CitaCancelarSerializer(serializers.Serializer):
    """Serializer para cancelar una cita"""
    motivo_cancelacion = serializers.CharField(
        required=True,
        min_length=10,
        error_messages={
            'required': 'El motivo de cancelación es requerido',
            'min_length': 'El motivo debe tener al menos 10 caracteres'
        }
    )
    
    def validate(self, data):
        """Validar que la cita puede ser cancelada"""
        # Esta validación se puede hacer en la vista si no se tiene acceso al instance
        return data

class CitaReprogramarSerializer(serializers.Serializer):
    """Serializer para reprogramar una cita"""
    nueva_fecha = serializers.DateField(required=True)
    nueva_hora_inicio = serializers.TimeField(required=True)
    
    def validate(self, data):
        fecha_hora_cita = timezone.make_aware(
            datetime.combine(data['nueva_fecha'], data['nueva_hora_inicio'])
        )
        if fecha_hora_cita < timezone.now():
            raise serializers.ValidationError(
                "No se pueden programar citas en el pasado"
            )
        return data

class CitaEstadoSerializer(serializers.Serializer):
    """Serializer para cambiar estado de cita"""
    estado = serializers.ChoiceField(
        choices=[
            EstadoCita.CONFIRMADA,
            EstadoCita.ASISTIDA,
            EstadoCita.NO_ASISTIDA,
            EstadoCita.EN_ATENCION
        ],
        required=True
    )

class HorariosDisponiblesSerializer(serializers.Serializer):
    """Serializer para consultar horarios disponibles"""
    odontologo = serializers.UUIDField(required=True)
    fecha = serializers.DateField(required=True)
    duracion = serializers.IntegerField(default=30, min_value=15, max_value=120)
    
    def validate_odontologo(self, value):
        """Validar que el odontólogo existe"""
        try:
            odontologo = Usuario.objects.get(id=value, rol='Odontologo', is_active=True)
            return value
        except Usuario.DoesNotExist:
            raise serializers.ValidationError("Odontólogo no encontrado")

class RecordatorioCitaSerializer(serializers.ModelSerializer):
    """Serializer para recordatorios"""
    cita_detalle = CitaSerializer(source='cita', read_only=True)
    
    class Meta:
        model = RecordatorioCita
        fields = [
            'id', 'cita', 'cita_detalle', 'tipo_recordatorio',
            'fecha_envio', 'enviado_exitosamente', 'mensaje', 'error'
        ]
        read_only_fields = ['id', 'fecha_envio']
