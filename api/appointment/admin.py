# api/appointment/admin.py
from django.contrib import admin
from .models import Cita, HorarioAtencion, RecordatorioCita


@admin.register(HorarioAtencion)
class HorarioAtencionAdmin(admin.ModelAdmin):
    """Admin para horarios de atención"""
    
    list_display = [
        'id',
        'odontologo',
        'get_dia_semana_display',
        'hora_inicio',
        'hora_fin',
        'duracion_cita',
        'activo',
        'fecha_creacion'
    ]
    
    list_filter = [
        'dia_semana',
        'activo',
        'odontologo',
        'fecha_creacion'
    ]
    
    search_fields = [
        'odontologo__nombres',
        'odontologo__apellidos',
        'odontologo__username'
    ]
    
    readonly_fields = [
        'id',
        'creado_por',
        'actualizado_por',
        'fecha_creacion',
        'fecha_modificacion'
    ]
    
    fieldsets = (
        ('Información del Horario', {
            'fields': ('odontologo', 'dia_semana', 'hora_inicio', 'hora_fin', 'duracion_cita')
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'actualizado_por', 'fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        })
    )
    
    def get_dia_semana_display(self, obj):
        return obj.get_dia_semana_display()
    get_dia_semana_display.short_description = 'Día'


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    """Admin para citas"""
    
    list_display = [
        'id',
        'paciente',
        'odontologo',
        'fecha',
        'hora_inicio',
        'hora_fin',
        'tipo_consulta',
        'estado',
        'activo',
        'fecha_creacion'
    ]
    
    list_filter = [
        'estado',
        'tipo_consulta',
        'fecha',
        'odontologo',
        'activo',
        'fecha_creacion'
    ]
    
    search_fields = [
        'paciente__nombres',
        'paciente__apellidos',
        'paciente__cedula_pasaporte',
        'odontologo__nombres',
        'odontologo__apellidos',
        'motivo_consulta'
    ]
    
    readonly_fields = [
        'id',
        'fecha_cancelacion',
        'fecha_atencion',
        'fecha_recordatorio',
        'creado_por',
        'actualizado_por',
        'fecha_creacion',
        'fecha_modificacion'
    ]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('paciente', 'odontologo')
        }),
        ('Fecha y Hora', {
            'fields': (('fecha', 'hora_inicio', 'hora_fin'), 'duracion')
        }),
        ('Detalles de la Cita', {
            'fields': ('tipo_consulta', 'estado', 'motivo_consulta', 'observaciones')
        }),
        ('Cancelación', {
            'fields': ('motivo_cancelacion', 'fecha_cancelacion', 'cancelada_por'),
            'classes': ('collapse',)
        }),
        ('Reprogramación', {
            'fields': ('cita_original',),
            'classes': ('collapse',)
        }),
        ('Atención', {
            'fields': ('fecha_atencion',),
            'classes': ('collapse',)
        }),
        ('Recordatorios', {
            'fields': ('recordatorio_enviado', 'fecha_recordatorio'),
            'classes': ('collapse',)
        }),
        ('Estado del Registro', {
            'fields': ('activo',)
        }),
        ('Auditoría', {
            'fields': ('creado_por', 'actualizado_por', 'fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        })
    )
    
    date_hierarchy = 'fecha'
    
    def get_queryset(self, request):
        """Optimizar consultas"""
        qs = super().get_queryset(request)
        return qs.select_related(
            'paciente', 'odontologo', 'creado_por',
            'cancelada_por', 'cita_original'
        )


@admin.register(RecordatorioCita)
class RecordatorioCitaAdmin(admin.ModelAdmin):
    """Admin para recordatorios"""
    
    list_display = [
        'id',
        'cita',
        'tipo_recordatorio',
        'fecha_envio',
        'enviado_exitosamente'
    ]
    
    list_filter = [
        'tipo_recordatorio',
        'enviado_exitosamente',
        'fecha_envio'
    ]
    
    search_fields = [
        'cita__paciente__nombres',
        'cita__paciente__apellidos',
        'mensaje'
    ]
    
    readonly_fields = [
        'id',
        'fecha_envio'
    ]
    
    fieldsets = (
        ('Información del Recordatorio', {
            'fields': ('cita', 'tipo_recordatorio')
        }),
        ('Estado del Envío', {
            'fields': ('enviado_exitosamente', 'fecha_envio', 'mensaje', 'error')
        })
    )
    
    date_hierarchy = 'fecha_envio'
    
    def get_queryset(self, request):
        """Optimizar consultas"""
        qs = super().get_queryset(request)
        return qs.select_related('cita', 'cita__paciente', 'cita__odontologo')
