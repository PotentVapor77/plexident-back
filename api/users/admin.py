from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'correo', 'nombres', 'apellidos', 'rol', 'is_staff', 'is_active')
    list_filter = ('rol', 'is_staff', 'is_active', 'status')
    search_fields = ('username', 'correo', 'nombres', 'apellidos')
    readonly_fields = ('created_by', 'updated_by', 'created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        ('Información Personal', {
            'fields': ('nombres', 'apellidos', 'correo', 'telefono', 'rol')
        }),
        ('Permisos', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Auditoría', {
            'fields': ('status', 'created_by', 'updated_by', 'created_at', 'updated_at')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'correo', 'nombres', 'apellidos', 'telefono', 'rol', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )