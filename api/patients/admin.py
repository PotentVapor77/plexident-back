# api/patients/admin.py
from django.contrib import admin
from django import forms  
from django.utils.html import format_html
from django.core.exceptions import ValidationError

# Importar modelos
from .models.paciente import Paciente
from .models.antecedentes_personales import AntecedentesPersonales
from .models.antecedentes_familiares import AntecedentesFamiliares
from .models.constantes_vitales import ConstantesVitales
from .models.examen_estomatognatico import ExamenEstomatognatico


# ================== PACIENTE ADMIN ==================
@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    
    # ================== CONFIGURACIÓN DE LISTADO ==================
    list_display = (
        'cedula_pasaporte',
        'get_nombre_completo',
        'get_sexo_display',
        'get_edad_completa',
        'telefono',
        'activo_display',
        'get_fecha_creacion'
    )
    
    list_filter = (
        'sexo',
        'activo',
        'condicion_edad',
        'fecha_creacion',
    )
    
    search_fields = (
        'nombres',
        'apellidos',
        'cedula_pasaporte',
        'telefono',
        'correo',
    )
    
    list_per_page = 20
    list_max_show_all = 100
    list_display_links = ('cedula_pasaporte', 'get_nombre_completo')
    ordering = ('apellidos', 'nombres')  
    readonly_fields = ('fecha_creacion', 'fecha_modificacion', 'creado_por', 'actualizado_por')
    
    # ================== FIELDSETS ORGANIZADOS ==================
    fieldsets = (
        # Sección A: DATOS PERSONALES
        ('Datos Personales', {
            'fields': (
                'nombres',
                'apellidos',
                ('cedula_pasaporte', 'fecha_nacimiento'),
                ('sexo', 'edad', 'condicion_edad'),
                'embarazada',
            ),
            'classes': ('wide', 'extrapretty'),
        }),
        
        # Sección A: CONTACTO
        ('Información de Contacto', {
            'fields': (
                'direccion',
                ('telefono', 'correo'),
                ('contacto_emergencia_nombre', 'contacto_emergencia_telefono'),
            ),
            'classes': ('wide',),
        }),
        
        # Sección B: MOTIVO DE CONSULTA
        ('Motivo de Consulta', {
            'fields': ('motivo_consulta',),
            'classes': ('wide',),
            'description': 'Sección B del formulario'
        }),
        
        # Sección C: ENFERMEDAD ACTUAL
        ('Enfermedad Actual', {
            'fields': ('enfermedad_actual',),
            'classes': ('wide',),
            'description': 'Sección C del formulario'
        }),
        
        # AUDITORÍA
        ('Auditoría', {
            'fields': (
                'activo',
                ('creado_por', 'actualizado_por'),
                ('fecha_creacion', 'fecha_modificacion'),
            ),
            'classes': ('collapse',),
        }),
    )
    
    # ================== MÉTODOS PARA CAMPOS PERSONALIZADOS ==================
    
    def get_nombre_completo(self, obj):
        """Muestra el nombre completo en el listado"""
        return obj.nombre_completo  
    get_nombre_completo.short_description = 'Nombre Completo'
    get_nombre_completo.admin_order_field = 'apellidos' 
    
    def get_sexo_display(self, obj):
        """Muestra el sexo"""
        return obj.get_sexo_display()
    get_sexo_display.short_description = 'Sexo'
    
    def get_edad_completa(self, obj):
        """Muestra la edad con condición"""
        return f"{obj.edad} {obj.get_condicion_edad_display()}"
    get_edad_completa.short_description = 'Edad'
    
    def activo_display(self, obj):
        """Muestra el estado activo con colores"""
        if obj.activo:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Activo</span>'
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">✗ Inactivo</span>'
        )
    activo_display.short_description = 'Estado'
    
    def get_fecha_creacion(self, obj):
        """Formatea la fecha de creación"""
        if obj.fecha_creacion:
            return obj.fecha_creacion.strftime('%d/%m/%Y')
        return '-'
    get_fecha_creacion.short_description = 'Creado'
    
    # ================== ACCIONES PERSONALIZADAS ==================
    actions = ['activar_pacientes', 'desactivar_pacientes']
    
    def activar_pacientes(self, request, queryset):
        """Acción para activar pacientes seleccionados"""
        updated = queryset.update(activo=True)
        self.message_user(
            request, 
            f'{updated} paciente(s) activado(s) exitosamente.',
            level='success'
        )
    activar_pacientes.short_description = "Activar pacientes seleccionados"
    
    def desactivar_pacientes(self, request, queryset):
        """Acción para desactivar pacientes seleccionados"""
        updated = queryset.update(activo=False)
        self.message_user(
            request, 
            f'{updated} paciente(s) desactivado(s) exitosamente.',
            level='success'
        )
    desactivar_pacientes.short_description = "Desactivar pacientes seleccionados"
    
    # ================== SOBRESCRITURA DE MÉTODOS ==================
    
    def get_readonly_fields(self, request, obj=None):
        """Campos de solo lectura"""
        readonly_fields = list(self.readonly_fields)
        
        if obj:  # Si estamos editando un objeto existente
            readonly_fields.append('cedula_pasaporte')  # No permitir cambiar la cédula
        
        return readonly_fields
    
    def get_form(self, request, obj=None, **kwargs):
        """Personaliza el formulario según el sexo"""
        form = super().get_form(request, obj, **kwargs)
        
        if obj and obj.sexo == 'M':
            # Ocultar campo embarazada para hombres
            form.base_fields['embarazada'].widget = forms.HiddenInput()
        
        return form
    
    def save_model(self, request, obj, form, change):
        """Guarda el modelo con el usuario actual"""
        if not obj.pk:
            # Nuevo paciente
            obj.creado_por = request.user
        else:
            # Actualización
            obj.actualizado_por = request.user
        
        # Validar que pacientes masculinos no tengan embarazada = SI
        if obj.sexo == 'M' and obj.embarazada == 'SI':
            raise ValidationError("Un paciente masculino no puede estar marcado como embarazado.")
        
        # Si es hombre, asegurar que embarazada sea None
        if obj.sexo == 'M':
            obj.embarazada = None
        
        super().save_model(request, obj, form, change)
    
    def save_formset(self, request, form, formset, change):
        """Guarda los formsets (modelos relacionados)"""
        instances = formset.save(commit=False)
        for instance in instances:
            if not instance.pk:
                # Si es una nueva instancia del modelo relacionado
                instance.creado_por = request.user
            else:
                instance.actualizado_por = request.user
            instance.save()
        formset.save_m2m()


# ================== REGISTRAR MODELOS RELACIONADOS SEPARADAMENTE ==================
@admin.register(AntecedentesPersonales)
class AntecedentesPersonalesAdmin(admin.ModelAdmin):
    list_display = ['paciente', 'alergia_antibiotico', 'alergia_anestesia']
    search_fields = ['paciente__nombres', 'paciente__apellidos']
    list_filter = ['alergia_antibiotico', 'alergia_anestesia']


@admin.register(AntecedentesFamiliares)
class AntecedentesFamiliaresAdmin(admin.ModelAdmin):
    list_display = ['paciente', 'cardiopatia_familiar', 'hipertension_arterial_familiar']
    search_fields = ['paciente__nombres', 'paciente__apellidos']


@admin.register(ConstantesVitales)
class ConstantesVitalesAdmin(admin.ModelAdmin):
    list_display = ['paciente', 'temperatura', 'pulso', 'presion_arterial']
    search_fields = ['paciente__nombres', 'paciente__apellidos']


@admin.register(ExamenEstomatognatico)
class ExamenEstomatognaticoAdmin(admin.ModelAdmin):
    list_display = ['paciente', 'examen_labios', 'examen_mejillas']
    search_fields = ['paciente__nombres', 'paciente__apellidos']
