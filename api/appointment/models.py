# api/appointment/models.py
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django_currentuser.db.models import CurrentUserField
from datetime import datetime, timedelta
import uuid


class EstadoCita(models.TextChoices):
    """Estados posibles de una cita"""
    PROGRAMADA = 'PROGRAMADA', 'Programada'
    CONFIRMADA = 'CONFIRMADA', 'Confirmada'
    ASISTIDA = 'ASISTIDA', 'Asistida'
    NO_ASISTIDA = 'NO_ASISTIDA', 'No Asistida'
    CANCELADA = 'CANCELADA', 'Cancelada'
    REPROGRAMADA = 'REPROGRAMADA', 'Reprogramada'
    EN_ATENCION = 'EN_ATENCION', 'En Atención'


class TipoConsulta(models.TextChoices):
    """Tipos de consulta odontológica"""
    PRIMERA_VEZ = 'PRIMERA_VEZ', 'Primera Vez'
    CONTROL = 'CONTROL', 'Control'
    URGENCIA = 'URGENCIA', 'Urgencia'
    LIMPIEZA = 'LIMPIEZA', 'Limpieza Dental'
    ORTODONCIA = 'ORTODONCIA', 'Ortodoncia'
    ENDODONCIA = 'ENDODONCIA', 'Endodoncia'
    CIRUGIA = 'CIRUGIA', 'Cirugía'
    PROTESIS = 'PROTESIS', 'Prótesis'
    SESION = 'SESION', 'Sesión'
    OTRO = 'OTRO', 'Otro'


class HorarioAtencion(models.Model):
    """Horarios de atención de los odontólogos"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    odontologo = models.ForeignKey(
        'users.Usuario',
        on_delete=models.CASCADE,
        related_name='horarios_atencion',
        limit_choices_to={'rol': 'Odontologo'},
        verbose_name="Odontólogo"
    )
    
    dia_semana = models.IntegerField(
        choices=[
            (0, 'Lunes'), (1, 'Martes'), (2, 'Miércoles'),
            (3, 'Jueves'), (4, 'Viernes'), (5, 'Sábado'), (6, 'Domingo'),
        ],
        verbose_name="Día de la semana"
    )
    
    hora_inicio = models.TimeField(verbose_name="Hora de inicio")
    hora_fin = models.TimeField(verbose_name="Hora de fin")
    duracion_cita = models.IntegerField(
        default=30,
        verbose_name="Duración de cita (minutos)"
    )
    
    activo = models.BooleanField(default=True)
    creado_por = CurrentUserField(related_name='horarios_creados', null=True, blank=True, editable=False)
    actualizado_por = CurrentUserField(on_update=True, related_name='horarios_actualizados', null=True, blank=True, editable=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Horario de Atención"
        verbose_name_plural = "Horarios de Atención"
        ordering = ['dia_semana', 'hora_inicio']
        unique_together = ['odontologo', 'dia_semana', 'hora_inicio']
    
    def __str__(self):
        dias = dict(self._meta.get_field('dia_semana').choices)
        return f"{self.odontologo.get_full_name()} - {dias[self.dia_semana]} {self.hora_inicio}-{self.hora_fin}"
    
    def clean(self):
        super().clean()
        if self.hora_inicio >= self.hora_fin:
            raise ValidationError("La hora de inicio debe ser menor que la hora de fin")


class Cita(models.Model):
    """Modelo de citas odontológicas"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    paciente = models.ForeignKey(
        'patients.Paciente',
        on_delete=models.CASCADE,
        related_name='citas',
        verbose_name="Paciente"
    )
    
    odontologo = models.ForeignKey(
        'users.Usuario',
        on_delete=models.CASCADE,
        related_name='citas_odontologo',
        limit_choices_to={'rol': 'Odontologo'},
        verbose_name="Odontólogo"
    )
    
    fecha = models.DateField(verbose_name="Fecha de la cita")
    hora_inicio = models.TimeField(verbose_name="Hora de inicio")
    hora_fin = models.TimeField(verbose_name="Hora de fin")
    
    duracion = models.IntegerField(default=30, verbose_name="Duración (minutos)")
    
    tipo_consulta = models.CharField(
        max_length=20,
        choices=TipoConsulta.choices,
        default=TipoConsulta.CONTROL,
        verbose_name="Tipo de consulta"
    )
    
    estado = models.CharField(
        max_length=20,
        choices=EstadoCita.choices,
        default=EstadoCita.PROGRAMADA,
        verbose_name="Estado"
    )
    
    motivo_consulta = models.TextField(blank=True, verbose_name="Motivo de consulta")
    observaciones = models.TextField(blank=True, verbose_name="Observaciones")
    
    # Campos para cancelación
    motivo_cancelacion = models.TextField(blank=True, verbose_name="Motivo de cancelación")
    fecha_cancelacion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de cancelación")
    cancelada_por = models.ForeignKey(
        'users.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='citas_canceladas',
        verbose_name="Cancelada por"
    )
    
    # Reprogramación
    cita_original = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='citas_reprogramadas',
        verbose_name="Cita original"
    )
    
    # Asistencia
    fecha_atencion = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de atención real")
    
    # Recordatorios
    recordatorio_enviado = models.BooleanField(default=False, verbose_name="Recordatorio enviado")
    fecha_recordatorio = models.DateTimeField(null=True, blank=True, verbose_name="Fecha recordatorio")
    
    # Auditoría
    activo = models.BooleanField(default=True)
    creado_por = CurrentUserField(related_name='citas_creadas', null=True, blank=True, editable=False)
    actualizado_por = CurrentUserField(on_update=True, related_name='citas_actualizadas', null=True, blank=True, editable=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Cita"
        verbose_name_plural = "Citas"
        ordering = ['-fecha', '-hora_inicio']
        indexes = [
            models.Index(fields=['fecha', 'odontologo']),
            models.Index(fields=['paciente', 'fecha']),
            models.Index(fields=['estado', 'fecha']),
        ]
    
    def __str__(self):
        return f"Cita: {self.paciente.nombre_completo} - {self.odontologo.get_full_name()} - {self.fecha} {self.hora_inicio}"
    
    def clean(self):
        super().clean()
        
        if self.hora_inicio >= self.hora_fin:
            raise ValidationError("La hora de inicio debe ser menor que la hora de fin")
        
        # Validar citas en el pasado (solo para nuevas)
        if not self.pk:
            fecha_hora_cita = timezone.make_aware(datetime.combine(self.fecha, self.hora_inicio))
            if fecha_hora_cita < timezone.now():
                raise ValidationError("No se pueden programar citas en el pasado")
        
        # Validar duplicidad
        if self.odontologo_id:
            citas_conflicto = Cita.objects.filter(
                odontologo=self.odontologo,
                fecha=self.fecha,
                activo=True
            ).exclude(estado__in=[EstadoCita.CANCELADA, EstadoCita.REPROGRAMADA])
            
            if self.pk:
                citas_conflicto = citas_conflicto.exclude(pk=self.pk)
            
            for cita in citas_conflicto:
                if (self.hora_inicio < cita.hora_fin and self.hora_fin > cita.hora_inicio):
                    raise ValidationError(
                        f"El odontólogo ya tiene una cita de {cita.hora_inicio} a {cita.hora_fin}"
                    )
        
        if self.estado == EstadoCita.CANCELADA and not self.motivo_cancelacion:
            raise ValidationError("Debe proporcionar un motivo de cancelación")
    
    def save(self, *args, **kwargs):
        if not self.hora_fin:
            hora_inicio_dt = datetime.combine(datetime.today(), self.hora_inicio)
            hora_fin_dt = hora_inicio_dt + timedelta(minutes=self.duracion)
            self.hora_fin = hora_fin_dt.time()
        super().save(*args, **kwargs)
    
    @property
    def esta_vigente(self):
        return self.estado not in [EstadoCita.CANCELADA, EstadoCita.REPROGRAMADA]
    
    @property
    def puede_ser_cancelada(self):
        """Define qué citas pueden ser canceladas"""
        # Estados en los que se permite cancelar
        estados_permitidos = [
            EstadoCita.PROGRAMADA, 
            EstadoCita.CONFIRMADA,
            EstadoCita.REPROGRAMADA  # ✅ AÑADIR ESTO: Permitir cancelar citas reprogramadas
        ]
        
        # Además, verificar que no sea en el pasado (solo para citas futuras)
        fecha_hora_cita = timezone.make_aware(
            datetime.combine(self.fecha, self.hora_inicio)
        )
        ahora = timezone.now()
        
        # ✅ CORRECCIÓN: Permitir cancelar citas pasadas si son reprogramadas
        if self.estado == EstadoCita.REPROGRAMADA:
            # Para citas reprogramadas, siempre permitir cancelar
            return True
        
        # Para otras citas, verificar que no sean en el pasado
        if fecha_hora_cita < ahora:
            return False
        
        return self.estado in estados_permitidos


class RecordatorioCita(models.Model):
    """Registro de recordatorios enviados - Solo WhatsApp y Email"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cita = models.ForeignKey(Cita, on_delete=models.CASCADE, related_name='recordatorios')
    
    destinatario = models.CharField(
        max_length=20,
        choices=[
            ('PACIENTE', 'Paciente'),
            ('ODONTOLOGO', 'Odontólogo'),
            ('AMBOS', 'Ambos'),
        ],
        default='PACIENTE'
    )
    
    # ✅  EMAIL
    tipo_recordatorio = models.CharField(
        max_length=20,
        choices=[
            ('EMAIL', 'Email'),
        ],
        default='EMAIL'  # Por defecto EMAIL
    )
    
    fecha_envio = models.DateTimeField(auto_now_add=True)
    enviado_exitosamente = models.BooleanField(default=False)
    mensaje = models.TextField(blank=True)
    error = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Recordatorio"
        verbose_name_plural = "Recordatorios"
        ordering = ['-fecha_envio']
    
    def __str__(self):
        return f"Recordatorio {self.tipo_recordatorio} - Cita {self.cita.id}"