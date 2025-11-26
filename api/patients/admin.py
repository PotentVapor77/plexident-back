from django.contrib import admin
from api.patients.models import Paciente

@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'nombres', 'apellidos', 'cedula_pasaporte',
        'fecha_nacimiento', 'sexo', 'telefono', 'correo',
        'contacto_emergencia_nombre', 'contacto_emergencia_telefono',
        'activo', 'fecha_creacion'
    )
    list_filter = ('sexo', 'activo', 'fecha_creacion')
    search_fields = ('nombres', 'apellidos', 'cedula_pasaporte', 'telefono', 'correo')
    readonly_fields = ('creado_por', 'actualizado_por', 'fecha_creacion', 'fecha_modificacion')

    fieldsets = (
        ('Datos Personales', {
            'fields': (
                'nombres', 'apellidos', 'cedula_pasaporte', 'fecha_nacimiento', 'sexo', 'direccion',
                'telefono', 'correo'
            )
        }),
        ('Emergencia', {
            'fields': (
                'contacto_emergencia_nombre', 'contacto_emergencia_telefono'
            )
        }),
        ('Seguridad', {
            'fields': (
                'alergias', 'enfermedades_sistemicas', 'habitos'
            )
        }),
        ('Auditoría', {
            'fields': (
                'activo', 'creado_por', 'actualizado_por', 'fecha_creacion', 'fecha_modificacion'
            )
        }),
    )