# api/appointment/serializers.py

from rest_framework import serializers

from api.parameters.models import ConfiguracionHorario
from .models import Cita, HistorialCita, HorarioAtencion, RecordatorioCita, EstadoCita
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
         CORRECCIÓN: Solo validar si ambos campos están presentes
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
        fields = ['paciente', 'odontologo', 'fecha', 'hora_inicio', 'duracion', 
                 'tipo_consulta', 'motivo_consulta', 'observaciones', 'estado']
        extra_kwargs = {
            'estado': {'required': False}
        }
    
    def create(self, validated_data):
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
        """✅ VALIDACIONES COMPLETAS CON HORARIOS"""
        fecha_cita = data['fecha']
        hora_cita = data['hora_inicio']
        odontologo = data['odontologo']
        ahora = timezone.now()
        
        # ✅ 1. Validar que no sea en el pasado
        if fecha_cita < ahora.date():
            raise serializers.ValidationError({
                'fecha': 'No se pueden programar citas en fechas pasadas'
            })
        
        if fecha_cita == ahora.date():
            fecha_hora_cita = timezone.make_aware(datetime.combine(fecha_cita, hora_cita))
            if fecha_hora_cita < ahora - timedelta(minutes=5):
                raise serializers.ValidationError({
                    'hora_inicio': 'La hora seleccionada ya pasó'
                })
        
        # ✅ 2. VALIDAR HORARIO GLOBAL DE LA CLÍNICA
        dia_semana = fecha_cita.weekday()  # 0=Lunes, 6=Domingo
        
        try:
            horario_clinica = ConfiguracionHorario.objects.get(
                dia_semana=dia_semana,
                activo=True
            )
        except ConfiguracionHorario.DoesNotExist:
            dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            raise serializers.ValidationError({
                'fecha': f'La clínica no atiende los días {dias[dia_semana]}'
            })
        
        # Validar que la hora esté dentro del horario de la clínica
        if hora_cita < horario_clinica.apertura:
            raise serializers.ValidationError({
                'hora_inicio': f'La clínica abre a las {horario_clinica.apertura.strftime("%H:%M")}. '
                             f'No puede agendar antes de ese horario.'
            })
        
        # Calcular hora fin de la cita
        duracion = data.get('duracion', 30)
        hora_fin_cita = (datetime.combine(fecha_cita, hora_cita) + timedelta(minutes=duracion)).time()
        
        if hora_fin_cita > horario_clinica.cierre:
            raise serializers.ValidationError({
                'hora_inicio': f'La clínica cierra a las {horario_clinica.cierre.strftime("%H:%M")}. '
                             f'Esta cita terminaría a las {hora_fin_cita.strftime("%H:%M")}.'
            })
        
        # ✅ 3. VALIDAR HORARIO DEL ODONTÓLOGO
        try:
            horario_doctor = HorarioAtencion.objects.get(
                odontologo=odontologo,
                dia_semana=dia_semana,
                activo=True
            )
        except HorarioAtencion.DoesNotExist:
            dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            raise serializers.ValidationError({
                'hora_inicio': f'El Dr(a). {odontologo.get_full_name()} no atiende los días {dias[dia_semana]}. '
                             f'Por favor configure su horario de atención primero.'
            })
        
        # Validar que la hora esté dentro del horario del doctor
        if hora_cita < horario_doctor.hora_inicio:
            raise serializers.ValidationError({
                'hora_inicio': f'El Dr(a). {odontologo.get_full_name()} inicia su atención a las '
                             f'{horario_doctor.hora_inicio.strftime("%H:%M")} los {dias[dia_semana]}.'
            })
        
        if hora_fin_cita > horario_doctor.hora_fin:
            raise serializers.ValidationError({
                'hora_inicio': f'El Dr(a). {odontologo.get_full_name()} termina su atención a las '
                             f'{horario_doctor.hora_fin.strftime("%H:%M")} los {dias[dia_semana]}. '
                             f'Esta cita terminaría a las {hora_fin_cita.strftime("%H:%M")}.'
            })
        
        return data














class CitaUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualizar citas"""
    
    class Meta:
        model = Cita
        fields = ['odontologo', 'fecha', 'hora_inicio', 'duracion', 
                 'tipo_consulta', 'motivo_consulta', 'observaciones', 'estado']
    
    def validate(self, data):
        """Validar que la cita puede ser actualizada"""
        instance = self.instance
        
        # Validar que la cita puede ser modificada
        if instance.estado in [EstadoCita.CANCELADA, EstadoCita.REPROGRAMADA]:
            raise serializers.ValidationError(
                "No se puede modificar una cita cancelada o reprogramada"
            )
        
        # ✅ SI SE CAMBIA FECHA/HORA, VALIDAR HORARIOS
        if 'fecha' in data or 'hora_inicio' in data:
            fecha = data.get('fecha', instance.fecha)
            hora_inicio = data.get('hora_inicio', instance.hora_inicio)
            odontologo = data.get('odontologo', instance.odontologo)
            duracion = data.get('duracion', instance.duracion)
            
            # Validar que no sea en el pasado
            fecha_hora_cita = timezone.make_aware(datetime.combine(fecha, hora_inicio))
            if fecha_hora_cita < timezone.now():
                raise serializers.ValidationError({
                    'fecha': 'No se pueden programar citas en el pasado'
                })
            
            # ✅ VALIDAR HORARIO CLÍNICA
            dia_semana = fecha.weekday()
            
            try:
                horario_clinica = ConfiguracionHorario.objects.get(
                    dia_semana=dia_semana,
                    activo=True
                )
            except ConfiguracionHorario.DoesNotExist:
                dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
                raise serializers.ValidationError({
                    'fecha': f'La clínica no atiende los días {dias[dia_semana]}'
                })
            
            hora_fin_cita = (datetime.combine(fecha, hora_inicio) + timedelta(minutes=duracion)).time()
            
            if not (horario_clinica.apertura <= hora_inicio < horario_clinica.cierre):
                raise serializers.ValidationError({
                    'hora_inicio': f'La clínica atiende de {horario_clinica.apertura.strftime("%H:%M")} '
                                 f'a {horario_clinica.cierre.strftime("%H:%M")}'
                })
            
            # ✅ VALIDAR HORARIO ODONTÓLOGO
            try:
                horario_doctor = HorarioAtencion.objects.get(
                    odontologo=odontologo,
                    dia_semana=dia_semana,
                    activo=True
                )
            except HorarioAtencion.DoesNotExist:
                dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
                raise serializers.ValidationError({
                    'hora_inicio': f'El Dr(a). {odontologo.get_full_name()} no atiende los {dias[dia_semana]}'
                })
            
            if not (horario_doctor.hora_inicio <= hora_inicio < horario_doctor.hora_fin):
                raise serializers.ValidationError({
                    'hora_inicio': f'El Dr(a). {odontologo.get_full_name()} atiende de '
                                 f'{horario_doctor.hora_inicio.strftime("%H:%M")} a '
                                 f'{horario_doctor.hora_fin.strftime("%H:%M")} los {dias[dia_semana]}'
                })
        
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
        """✅ VALIDAR HORARIOS EN REPROGRAMACIÓN"""
        nueva_fecha = data['nueva_fecha']
        nueva_hora = data['nueva_hora_inicio']
        
        # Obtener la cita original del contexto
        cita_original = self.context.get('cita')
        if not cita_original:
            raise serializers.ValidationError("No se proporcionó la cita original")
        
        odontologo = cita_original.odontologo
        duracion = cita_original.duracion
        
        # Validar que no sea en el pasado
        fecha_hora_cita = timezone.make_aware(datetime.combine(nueva_fecha, nueva_hora))
        if fecha_hora_cita < timezone.now():
            raise serializers.ValidationError(
                "No se pueden programar citas en el pasado"
            )
        
        # ✅ VALIDAR HORARIO CLÍNICA
        dia_semana = nueva_fecha.weekday()
        
        try:
            horario_clinica = ConfiguracionHorario.objects.get(
                dia_semana=dia_semana,
                activo=True
            )
        except ConfiguracionHorario.DoesNotExist:
            dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            raise serializers.ValidationError({
                'nueva_fecha': f'La clínica no atiende los días {dias[dia_semana]}'
            })
        
        hora_fin = (datetime.combine(nueva_fecha, nueva_hora) + timedelta(minutes=duracion)).time()
        
        if not (horario_clinica.apertura <= nueva_hora < horario_clinica.cierre):
            raise serializers.ValidationError({
                'nueva_hora_inicio': f'La clínica atiende de {horario_clinica.apertura.strftime("%H:%M")} '
                                    f'a {horario_clinica.cierre.strftime("%H:%M")}'
            })
        
        # ✅ VALIDAR HORARIO ODONTÓLOGO
        try:
            horario_doctor = HorarioAtencion.objects.get(
                odontologo=odontologo,
                dia_semana=dia_semana,
                activo=True
            )
        except HorarioAtencion.DoesNotExist:
            dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            raise serializers.ValidationError({
                'nueva_hora_inicio': f'El Dr(a). {odontologo.get_full_name()} no atiende los {dias[dia_semana]}'
            })
        
        if not (horario_doctor.hora_inicio <= nueva_hora < horario_doctor.hora_fin):
            raise serializers.ValidationError({
                'nueva_hora_inicio': f'El Dr(a). {odontologo.get_full_name()} atiende de '
                                    f'{horario_doctor.hora_inicio.strftime("%H:%M")} a '
                                    f'{horario_doctor.hora_fin.strftime("%H:%M")}'
            })
        
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
    """Serializer para recordatorios - Solo Email"""
    cita_detalle = CitaSerializer(source='cita', read_only=True)
    destinatario_display = serializers.CharField(source='get_destinatario_display', read_only=True)
    tipo_recordatorio_display = serializers.CharField(source='get_tipo_recordatorio_display', read_only=True)
    
    # Campos adicionales para estadísticas
    email_destinatario = serializers.SerializerMethodField(read_only=True)
    paciente_nombre = serializers.SerializerMethodField(read_only=True)
    odontologo_nombre = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = RecordatorioCita
        fields = [
            'id', 'cita', 'cita_detalle', 'destinatario', 'destinatario_display',
            'tipo_recordatorio', 'tipo_recordatorio_display', 'fecha_envio', 
            'enviado_exitosamente', 'mensaje', 'error',
            'email_destinatario', 'paciente_nombre', 'odontologo_nombre'  # Campos adicionales
        ]
        read_only_fields = ['id', 'fecha_envio']
    
    def get_email_destinatario(self, obj):
        """Obtiene el email del destinatario"""
        if obj.destinatario == 'PACIENTE':
            return obj.cita.paciente.correo if obj.cita.paciente.correo else None
        elif obj.destinatario == 'ODONTOLOGO':
            return obj.cita.odontologo.correo if obj.cita.odontologo.correo else None
        return None
    
    def get_paciente_nombre(self, obj):
        """Obtiene nombre del paciente"""
        return obj.cita.paciente.nombre_completo if obj.cita.paciente else None
    
    def get_odontologo_nombre(self, obj):
        """Obtiene nombre del odontólogo"""
        return obj.cita.odontologo.get_full_name() if obj.cita.odontologo else None
    
    def validate_tipo_recordatorio(self, value):
        """Validar que solo sea EMAIL"""
        if value != 'EMAIL':
            raise serializers.ValidationError(
                f"Solo EMAIL es permitido. Recibido: {value}"
            )
        return value


class RecordatorioEnvioSerializer(serializers.Serializer):
    """Serializer para enviar recordatorios"""
    tipo_recordatorio = serializers.ChoiceField(
        choices=['EMAIL'],
        default='EMAIL',
        help_text="Tipo de recordatorio a enviar (solo EMAIL disponible)"
    )
    
    destinatario = serializers.ChoiceField(
        choices=['PACIENTE', 'ODONTOLOGO', 'AMBOS'],
        default='PACIENTE',
        help_text="Destinatario del recordatorio"
    )
    
    mensaje = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="Mensaje personalizado adicional (opcional)"
    )
    
    def validate(self, data):
        """Validaciones adicionales"""
        tipo_recordatorio = data.get('tipo_recordatorio', 'EMAIL')
        destinatario = data.get('destinatario', 'PACIENTE')
        
        if tipo_recordatorio != 'EMAIL':
            raise serializers.ValidationError({
                'tipo_recordatorio': 'Solo se permite EMAIL'
            })
        
        return data


class RecordatorioEstadisticaSerializer(serializers.Serializer):
    """Serializer para estadísticas de recordatorios"""
    total_enviados = serializers.IntegerField(read_only=True)
    exitosos = serializers.IntegerField(read_only=True)
    fallidos = serializers.IntegerField(read_only=True)
    tasa_exito = serializers.FloatField(read_only=True)
    por_destinatario = serializers.DictField(read_only=True)
    por_mes = serializers.ListField(read_only=True)
    ultimos_recordatorios = RecordatorioCitaSerializer(many=True, read_only=True)


class HistorialCitaSerializer(serializers.ModelSerializer):
    """Serializer para historial de cambios de citas"""
    usuario_nombre = serializers.SerializerMethodField()
    accion_display = serializers.CharField(source='get_accion_display', read_only=True)
    
    class Meta:
        model = HistorialCita
        fields = [
            'id', 'cita', 'fecha_cambio', 'usuario', 'usuario_nombre',
            'accion', 'accion_display', 'datos_anteriores', 'datos_nuevos',
            'descripcion'
        ]
        read_only_fields = ['id', 'fecha_cambio']
    
    def get_usuario_nombre(self, obj):
        return obj.usuario.get_full_name() if obj.usuario else 'Sistema'