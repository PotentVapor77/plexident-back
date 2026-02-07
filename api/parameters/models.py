# api/parameters/models.py
from django.db import models
import uuid
from django_currentuser.db.models import CurrentUserField

class ConfiguracionHorario(models.Model):
    """Configuración de horarios de atención de la clínica (RF-07.1)"""
    DIAS_SEMANA = [
        (0, 'Lunes'),
        (1, 'Martes'),
        (2, 'Miércoles'),
        (3, 'Jueves'),
        (4, 'Viernes'),
        (5, 'Sábado'),
        (6, 'Domingo'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dia_semana = models.IntegerField(choices=DIAS_SEMANA)
    apertura = models.TimeField()
    cierre = models.TimeField()
    activo = models.BooleanField(default=True)
    
    # Auditoría
    creado_por = CurrentUserField(
        related_name='config_horarios_creados',
        null=True,
        blank=True,
        editable=False
    )
    actualizado_por = CurrentUserField(
        on_update=True,
        related_name='config_horarios_actualizados',
        null=True,
        blank=True,
        editable=False
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['dia_semana']
        verbose_name = 'Configuración de horario'
        verbose_name_plural = 'Configuraciones de horarios'
        ordering = ['dia_semana']
    
    def __str__(self):
        return f"{self.get_dia_semana_display()}: {self.apertura} - {self.cierre}"


class DiagnosticoFrecuente(models.Model):
    CATEGORIAS_DIAGNOSTICO = [
        ('CARIES', 'Caries'),
        ('ENFERMEDAD_PERIODONTAL', 'Enfermedad Periodontal'),
        ('ORTODONCIA', 'Ortodoncia'),
        ('ENDODONCIA', 'Endodoncia'),
        ('CIRUGIA', 'Cirugía'),
        ('PROTESIS', 'Prótesis'),
        ('PREVENTIVO', 'Preventivo'),
        ('OTRO', 'Otro'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    categoria = models.CharField(max_length=50, choices=CATEGORIAS_DIAGNOSTICO)
    activo = models.BooleanField(default=True)
    
    # Auditoría
    creado_por = CurrentUserField(
        related_name='diagnosticos_creados',
        null=True,
        blank=True,
        editable=False
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Diagnóstico frecuente'
        verbose_name_plural = 'Diagnósticos frecuentes'
        ordering = ['categoria', 'nombre']
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class MedicamentoFrecuente(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=200)
    principio_activo = models.CharField(max_length=200, blank=True)
    presentacion = models.CharField(max_length=100)
    dosis_habitual = models.CharField(max_length=100)
    via_administracion = models.CharField(max_length=50, default='Oral')
    categoria = models.CharField(max_length=100, blank=True)
    activo = models.BooleanField(default=True)
    
    # Auditoría
    creado_por = CurrentUserField(
        related_name='medicamentos_creados',
        null=True,
        blank=True,
        editable=False
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Medicamento frecuente'
        verbose_name_plural = 'Medicamentos frecuentes'
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.nombre} ({self.presentacion})"


class ConfiguracionSeguridad(models.Model):
    """Configuración de seguridad del sistema - solo un registro"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Tiempo de inactividad (RF-07.4)
    tiempo_inactividad_minutos = models.IntegerField(
        default=30,
        verbose_name='Tiempo de inactividad (minutos)',
        help_text='Minutos de inactividad antes de cerrar sesión automáticamente'
    )
    
    # Intentos de login (RF-07.4)
    max_intentos_login = models.IntegerField(
        default=5,
        verbose_name='Máximo intentos de login',
        help_text='Número máximo de intentos fallidos antes de bloquear'
    )
    
    duracion_bloqueo_minutos = models.IntegerField(
        default=15,
        verbose_name='Duración de bloqueo (minutos)',
        help_text='Minutos que permanece bloqueada la cuenta después de intentos fallidos'
    )
    
    # Complejidad de contraseñas (RF-07.5)
    longitud_minima_password = models.IntegerField(
        default=8,
        verbose_name='Longitud mínima de contraseña'
    )
    
    requiere_mayusculas = models.BooleanField(
        default=True,
        verbose_name='Requerir mayúsculas'
    )
    
    requiere_numeros = models.BooleanField(
        default=True,
        verbose_name='Requerir números'
    )
    
    requiere_especiales = models.BooleanField(
        default=False,
        verbose_name='Requerir caracteres especiales'
    )
    
    # Historial de contraseñas
    historial_password_cantidad = models.IntegerField(
        default=3,
        verbose_name='Cantidad de contraseñas anteriores a recordar',
        help_text='Evita reutilizar las últimas N contraseñas'
    )
    
    dias_validez_password = models.IntegerField(
        default=90,
        verbose_name='Días de validez de contraseña',
        help_text='Número de días antes de requerir cambio de contraseña'
    )
    
    # Auditoría
    actualizado_por = CurrentUserField(
        on_update=True,
        related_name='seguridad_actualizada',
        null=True,
        blank=True,
        editable=False
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Configuración de seguridad'
        verbose_name_plural = 'Configuraciones de seguridad'
    
    def save(self, *args, **kwargs):
        if not self.pk and ConfiguracionSeguridad.objects.exists():
            existing = ConfiguracionSeguridad.objects.first()
            self.pk = existing.pk
        super().save(*args, **kwargs)
    
    def __str__(self):
        return 'Configuración de Seguridad del Sistema'


class ConfiguracionNotificaciones(models.Model):
    """Configuración de notificaciones - solo un registro"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Recordatorios de citas (RF-07.7)
    recordatorio_citas_horas_antes = models.IntegerField(
        default=24,
        verbose_name='Recordatorio de citas (horas antes)',
        help_text='Horas de anticipación para recordatorios de citas'
    )
    
    # Tipos de recordatorio
    enviar_email = models.BooleanField(
        default=True,
        verbose_name='Enviar notificaciones por email'
    )
    
    enviar_sms = models.BooleanField(
        default=False,
        verbose_name='Enviar notificaciones por SMS'
    )
    
    # Horarios de envío
    hora_envio_diaria = models.TimeField(
        default='09:00',
        verbose_name='Hora de envío diario',
        help_text='Hora para enviar recordatorios programados'
    )
    
    # Configuración de email
    asunto_email_recordatorio = models.CharField(
        max_length=200,
        default='Recordatorio de cita - FamySALUD',
        verbose_name='Asunto del email de recordatorio'
    )
    
    # Configuración de SMS
    plantilla_sms = models.CharField(
        max_length=160,
        default='Recordatorio: Tiene cita el {fecha} a las {hora} en FamySALUD',
        verbose_name='Plantilla de SMS'
    )
    
    # Auditoría
    actualizado_por = CurrentUserField(
        on_update=True,
        related_name='notificaciones_actualizadas',
        null=True,
        blank=True,
        editable=False
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Configuración de notificaciones'
        verbose_name_plural = 'Configuraciones de notificaciones'
    
    def save(self, *args, **kwargs):
        if not self.pk and ConfiguracionNotificaciones.objects.exists():
            existing = ConfiguracionNotificaciones.objects.first()
            self.pk = existing.pk
        super().save(*args, **kwargs)
    
    def __str__(self):
        return 'Configuración de Notificaciones'


class ParametroGeneral(models.Model):
    """Parámetros generales del sistema"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    clave = models.CharField(max_length=100, unique=True)
    valor = models.TextField()
    descripcion = models.TextField(blank=True)
    categoria = models.CharField(max_length=50)
    tipo = models.CharField(max_length=20, choices=[
        ('STRING', 'Texto'),
        ('INTEGER', 'Número entero'),
        ('FLOAT', 'Número decimal'),
        ('BOOLEAN', 'Verdadero/Falso'),
        ('JSON', 'JSON'),
    ], default='STRING')
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Parámetro general'
        verbose_name_plural = 'Parámetros generales'
        ordering = ['categoria', 'clave']
    
    def __str__(self):
        return f"{self.clave} = {self.valor}"