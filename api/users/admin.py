from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import PermisoUsuario, Usuario

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ('username', 'password' , 'correo', 'nombres', 'apellidos', 'rol', 'is_staff', 'is_active')
    list_filter = ('rol', 'is_staff', 'is_active')
    search_fields = ('username', 'correo', 'nombres', 'apellidos')
    readonly_fields = ('creado_por', 'actualizado_por', 'fecha_creacion', 'fecha_modificacion')
    
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
            'fields': ( 'creado_por', 'actualizado_por', 'fecha_creacion', 'fecha_modificacion')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'correo', 'nombres', 'apellidos', 'telefono', 'rol', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )

@admin.register(PermisoUsuario)
class PermisoUsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'modelo', 'metodos_permitidos')
    list_filter = ('modelo', 'usuario__rol')
    search_fields = ('usuario__username', 'usuario__nombres', 'usuario__apellidos')
    autocomplete_fields = ['usuario']

