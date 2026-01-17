from django.contrib import admin
from api.clinical_records.models import ClinicalRecord


@admin.register(ClinicalRecord)
class ClinicalRecordAdmin(admin.ModelAdmin):
    list_display = ('id', 'paciente', 'odontologo_responsable', 'fecha_atencion', 'estado', 'activo')
    list_filter = ('estado', 'activo', 'fecha_atencion')
    search_fields = ('paciente__nombres', 'paciente__apellidos', 'paciente__cedula_pasaporte', 'motivo_consulta')
    readonly_fields = ('id', 'fecha_atencion', 'fecha_creacion', 'fecha_modificacion', 'fecha_cierre', 'creado_por', 'actualizado_por')
    
    fieldsets = (
        ('Información del Paciente', {
            'fields': ('paciente', 'odontologo_responsable', 'estado')
        }),
        ('Sección B y C: Motivo y Enfermedad Actual', {
            'fields': ('motivo_consulta', 'embarazada', 'enfermedad_actual')
        }),
        ('Secciones D-G: Referencias a Datos Clínicos', {
            'fields': ('antecedentes_personales', 'antecedentes_familiares', 'constantes_vitales', 'examen_estomatognatico')
        }),
        ('Datos Administrativos', {
            'fields': ('institucion_sistema', 'unicodigo', 'establecimiento_salud', 'numero_hoja')
        }),
        ('Observaciones', {
            'fields': ('observaciones',)
        }),
        ('Metadatos', {
            'fields': ('fecha_atencion', 'fecha_cierre', 'activo', 'creado_por', 'actualizado_por', 'fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:  # Si es creación
            obj.creado_por = request.user
        obj.actualizado_por = request.user
        super().save_model(request, obj, form, change)
