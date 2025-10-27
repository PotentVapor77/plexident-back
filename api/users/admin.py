from django.contrib import admin
from .models import Usuario

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('id_usuario', 'nombres', 'apellidos', 'username', 'correo', 'rol', 'status', 'created_at')
    list_filter = ('rol', 'status')
    search_fields = ('nombres', 'apellidos', 'correo')
    readonly_fields = ('created_by', 'updated_by', 'created_at', 'updated_at')

    fieldsets = (
        ('Datos Personales', {
            'fields': ('nombres', 'apellidos', 'imagen_perfil','contrasena_hash' , 'telefono', 'correo', 'rol')
        }),
        ('Seguridad y Auditoría', {
            'fields': ('status', 'created_by', 'updated_by', 'created_at', 'updated_at')
        }),
    )
