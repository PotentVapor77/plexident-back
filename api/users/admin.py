from django.contrib import admin
from .models import Usuario

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombres', 'apellidos', 'username', 'correo', 'rol', 'status', 'created_at')
    list_filter = ('rol', 'status')
    search_fields = ('nombres', 'apellidos', 'correo', 'username')
    readonly_fields = ('created_by', 'updated_by', 'created_at', 'updated_at', 'username')

    fieldsets = (
        ('Datos Personales', {
            'fields': ('nombres', 'apellidos', 'imagen_perfil', 'telefono', 'correo', 'rol')
        }),
        ('Credenciales', {
            'fields': ('username', 'contrasena_hash')
        }),
        ('Seguridad y Auditoría', {
            'fields': ('status', 'created_by', 'updated_by', 'created_at', 'updated_at')
        }),
    )
