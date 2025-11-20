from django.contrib import admin
from api.patients.models import Paciente

@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'nombres', 'apellidos', 'cedula_pasaporte',
        'fecha_nacimiento', 'sexo', 'telefono', 'correo',
        'contacto_emergencia_nombre', 'contacto_emergencia_telefono',
        'status', 'created_at'
    )
    list_filter = ('sexo', 'status', 'created_at')
    search_fields = ('nombres', 'apellidos', 'cedula_pasaporte', 'telefono', 'correo')
    readonly_fields = ('created_by', 'updated_by', 'created_at', 'updated_at')

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
                'status', 'created_by', 'updated_by', 'created_at', 'updated_at'
            )
        }),
    )