# api/patients/admin.py
from django.contrib import admin
from django import forms  
from django.utils.html import format_html
from django.core.exceptions import ValidationError

from api.patients.models.anamnesis_general import AnamnesisGeneral

from .models.examen_estomatognatico import ExamenEstomatognatico

# Importar modelos
from .models.paciente import Paciente
from .models.antecedentes_personales import AntecedentesPersonales
from .models.antecedentes_familiares import AntecedentesFamiliares
from .models.constantes_vitales import ConstantesVitales
#from .models.examen_estomatognatico import ExamenEstomatognatico


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




@admin.register(ExamenEstomatognatico)
class ExamenEstomatognaticoAdmin(admin.ModelAdmin):
    list_display = [
        'paciente', 
        'examen_sin_patologia',
        'tiene_patologias',
        'activo',
        'fecha_creacion'
    ]
    
    list_filter = [
        'examen_sin_patologia',
        'activo',
        'atm_cp',
        'mejillas_cp',
        'fecha_creacion'
    ]
    
    search_fields = [
        'paciente__nombres', 
        'paciente__apellidos',
        'paciente__cedula_pasaporte'
    ]
    
    readonly_fields = ['fecha_creacion', 'fecha_modificacion']
    
    fieldsets = (
        ('Información del Paciente', {
            'fields': ('paciente', 'examen_sin_patologia')
        }),
        ('ATM - Articulación Temporomandibular', {
            'fields': (
                ('atm_cp', 'atm_sp'),
                ('atm_absceso', 'atm_fibroma', 'atm_herpes'),
                ('atm_ulcera', 'atm_otra_patologia'),
                'atm_observacion'
            )
        }),
        ('Mejillas', {
            'fields': (
                ('mejillas_cp', 'mejillas_sp'),
                ('mejillas_absceso', 'mejillas_fibroma', 'mejillas_herpes'),
                ('mejillas_ulcera', 'mejillas_otra_patologia'),
                'mejillas_descripcion'
            ),
            'classes': ('collapse',)
        }),
        ('Maxilar Inferior', {
            'fields': (
                ('maxilar_inferior_cp', 'maxilar_inferior_sp'),
                ('maxilar_inferior_absceso', 'maxilar_inferior_fibroma', 'maxilar_inferior_herpes'),
                ('maxilar_inferior_ulcera', 'maxilar_inferior_otra_patologia'),
                'maxilar_inferior_descripcion'
            ),
            'classes': ('collapse',)
        }),
        ('Maxilar Superior', {
            'fields': (
                ('maxilar_superior_cp', 'maxilar_superior_sp'),
                ('maxilar_superior_absceso', 'maxilar_superior_fibroma', 'maxilar_superior_herpes'),
                ('maxilar_superior_ulcera', 'maxilar_superior_otra_patologia'),
                'maxilar_superior_descripcion'
            ),
            'classes': ('collapse',)
        }),
        ('Paladar', {
            'fields': (
                ('paladar_cp', 'paladar_sp'),
                ('paladar_absceso', 'paladar_fibroma', 'paladar_herpes'),
                ('paladar_ulcera', 'paladar_otra_patologia'),
                'paladar_descripcion'
            ),
            'classes': ('collapse',)
        }),
        ('Piso de Boca', {
            'fields': (
                ('piso_boca_cp', 'piso_boca_sp'),
                ('piso_boca_absceso', 'piso_boca_fibroma', 'piso_boca_herpes'),
                ('piso_boca_ulcera', 'piso_boca_otra_patologia'),
                'piso_boca_descripcion'
            ),
            'classes': ('collapse',)
        }),
        ('Carrillos', {
            'fields': (
                ('carrillos_cp', 'carrillos_sp'),
                ('carrillos_absceso', 'carrillos_fibroma', 'carrillos_herpes'),
                ('carrillos_ulcera', 'carrillos_otra_patologia'),
                'carrillos_descripcion'
            ),
            'classes': ('collapse',)
        }),
        ('Glándulas Salivales', {
            'fields': (
                ('glandulas_salivales_cp', 'glandulas_salivales_sp'),
                ('glandulas_salivales_absceso', 'glandulas_salivales_fibroma', 'glandulas_salivales_herpes'),
                ('glandulas_salivales_ulcera', 'glandulas_salivales_otra_patologia'),
                'glandulas_salivales_descripcion'
            ),
            'classes': ('collapse',)
        }),
        ('Ganglios de Cabeza y Cuello', {
            'fields': (
                ('ganglios_cp', 'ganglios_sp'),
                ('ganglios_absceso', 'ganglios_fibroma', 'ganglios_herpes'),
                ('ganglios_ulcera', 'ganglios_otra_patologia'),
                'ganglios_descripcion'
            ),
            'classes': ('collapse',)
        }),
        ('Lengua', {
            'fields': (
                ('lengua_cp', 'lengua_sp'),
                ('lengua_absceso', 'lengua_fibroma', 'lengua_herpes'),
                ('lengua_ulcera', 'lengua_otra_patologia'),
                'lengua_descripcion'
            ),
            'classes': ('collapse',)
        }),
        ('Labios', {
            'fields': (
                ('labios_cp', 'labios_sp'),
                ('labios_absceso', 'labios_fibroma', 'labios_herpes'),
                ('labios_ulcera', 'labios_otra_patologia'),
                'labios_descripcion'
            ),
            'classes': ('collapse',)
        }),
        ('Estado', {
            'fields': ('activo', 'fecha_creacion', 'fecha_modificacion')
        })
    )



# ============================================================================
# ✅ NUEVO: CONSULTA ADMIN
# ============================================================================
@admin.register(ConstantesVitales)
class ConstantesVitalesAdmin(admin.ModelAdmin):
    list_display = [
        'paciente', 
        'fecha_consulta',
        'temperatura', 
        'pulso', 
        'presion_arterial',
        'activo'
    ]
    
    list_filter = [
        'fecha_consulta',
        'activo',
    ]
    
    search_fields = [
        'paciente__nombres', 
        'paciente__apellidos',
        'motivo_consulta',
        'enfermedad_actual'
    ]
    
    readonly_fields = [
        'fecha_creacion', 
        'fecha_modificacion',
        'creado_por', 
        'actualizado_por'
    ]
    
    fieldsets = (
        ('Información del Paciente', {
            'fields': ('paciente', 'fecha_consulta', 'activo')
        }),
        ('Motivo y Enfermedad', {
            'fields': ('motivo_consulta', 'enfermedad_actual'),
            'classes': ('wide',)
        }),
        ('Constantes Vitales', {
            'fields': (
                ('temperatura', 'pulso'),
                ('frecuencia_respiratoria', 'presion_arterial')
            )
        }),
        ('Observaciones', {
            'fields': ('observaciones',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': (
                'creado_por',
                'actualizado_por',
                'fecha_creacion',
                'fecha_modificacion'
            ),
            'classes': ('collapse',)
        }),
    )
    
    date_hierarchy = 'fecha_consulta'
    ordering = ['-fecha_consulta']


@admin.register(AnamnesisGeneral)
class AnamnesisGeneralAdmin(admin.ModelAdmin):
    list_display = [
        'paciente',
        'get_alergias_display',
        'get_hemorragias_display',  # ✅ CAMBIADO
        'get_condiciones_criticas_display',
        'activo',
        'fecha_creacion'
    ]
    
    list_display_links = ['paciente']
    
    search_fields = [
        'paciente__nombres',
        'paciente__apellidos',
        'paciente__cedula_pasaporte',
        'observaciones',
        'alergia_antibiotico_otro',
        'alergia_anestesia_otro',
        'hemorragias_detalle',  # ✅ AÑADIDO
        'otro_antecedente_personal',  # ✅ AÑADIDO
        'otro_antecedente_familiar'  # ✅ AÑADIDO
    ]
    
    list_filter = [
        'activo',
        'hemorragias',  # ✅ CAMBIADO
        'alergia_antibiotico',
        'alergia_anestesia',
        'vih_sida',
        'diabetes',
        'hipertension_arterial',  # ✅ CAMBIADO
        'enfermedad_cardiaca',
        'fecha_creacion'
    ]
    
    raw_id_fields = ['paciente']
    
    readonly_fields = [
        'fecha_creacion',
        'fecha_modificacion',
        'creado_por',
        'actualizado_por',
        'resumen_condiciones_display'
    ]
    
    fieldsets = (
        ('Información del Paciente', {
            'fields': ('paciente', 'activo')
        }),
        
        ('Alergias', {
            'fields': (
                ('alergia_antibiotico', 'alergia_antibiotico_otro'),
                ('alergia_anestesia', 'alergia_anestesia_otro'),
            )
        }),
        
        ('Hemorragias / Problemas de Coagulación', {  # ✅ CAMBIADO
            'fields': (
                'hemorragias',
                'hemorragias_detalle'
            )
        }),
        
        ('Antecedentes Personales', {
            'fields': (
                ('vih_sida', 'vih_sida_otro'),
                ('tuberculosis', 'tuberculosis_otro'),
                ('asma', 'asma_otro'),
                ('diabetes', 'diabetes_otro'),
                ('hipertension_arterial', 'hipertension_arterial_otro'),  # ✅ CAMBIADO
                ('enfermedad_cardiaca', 'enfermedad_cardiaca_otro'),  # ✅ CAMBIADO
                'otro_antecedente_personal'  # ✅ AÑADIDO
            ),
            'classes': ('wide',)
        }),
        
        ('Antecedentes Familiares', {
            'fields': (
                ('cardiopatia_familiar', 'cardiopatia_familiar_otro'),
                ('hipertension_familiar', 'hipertension_familiar_otro'),
                ('enfermedad_cerebrovascular_familiar', 'enfermedad_cerebrovascular_familiar_otro'),
                ('endocrino_metabolico_familiar', 'endocrino_metabolico_familiar_otro'),
                ('cancer_familiar', 'cancer_familiar_otro'),
                ('tuberculosis_familiar', 'tuberculosis_familiar_otro'),
                ('enfermedad_mental_familiar', 'enfermedad_mental_familiar_otro'),
                ('enfermedad_infecciosa_familiar', 'enfermedad_infecciosa_familiar_otro'),
                ('malformacion_familiar', 'malformacion_familiar_otro'),
                'otro_antecedente_familiar'  # ✅ AÑADIDO
            ),
            'classes': ('wide',)
        }),
        
        ('Hábitos y Observaciones', {
            'fields': (
                'habitos',
                'observaciones'
            )
        }),
        
        ('Resumen', {
            'fields': ('resumen_condiciones_display',),
            'classes': ('collapse',)
        }),
        
        ('Metadata', {
            'fields': (
                'fecha_creacion',
                'fecha_modificacion',
                'creado_por',
                'actualizado_por'
            ),
            'classes': ('collapse',)
        }),
    )
    
    def get_alergias_display(self, obj):
        """Muestra alergias en lista"""
        alergias = []
        if obj.alergia_antibiotico != 'NO':
            texto = f"Antibióticos: {obj.get_alergia_antibiotico_display()}"
            if obj.alergia_antibiotico == 'OTRO' and obj.alergia_antibiotico_otro:
                texto += f" ({obj.alergia_antibiotico_otro})"
            alergias.append(texto)
        
        if obj.alergia_anestesia != 'NO':
            texto = f"Anestesia: {obj.get_alergia_anestesia_display()}"
            if obj.alergia_anestesia == 'OTRO' and obj.alergia_anestesia_otro:
                texto += f" ({obj.alergia_anestesia_otro})"
            alergias.append(texto)
        
        return format_html('<br>'.join(alergias)) if alergias else 'Sin alergias'
    get_alergias_display.short_description = 'Alergias'
    
    def get_hemorragias_display(self, obj):  # ✅ NUEVO MÉTODO
        """Muestra información de hemorragias"""
        if obj.hemorragias == 'SI':
            if obj.hemorragias_detalle:
                return format_html(
                    '<span style="color: red; font-weight: bold;">⚠️ HEMORRAGIAS</span><br>'
                    '<small>{}</small>', 
                    obj.hemorragias_detalle[:50] + '...' if len(obj.hemorragias_detalle) > 50 else obj.hemorragias_detalle
                )
            return format_html('<span style="color: red; font-weight: bold;">⚠️ HEMORRAGIAS</span>')
        return 'Sin problemas'
    get_hemorragias_display.short_description = 'Hemorragias'
    
    def get_condiciones_criticas_display(self, obj):
        """Muestra condiciones críticas en lista"""
        condiciones = []
        if obj.hemorragias == 'SI':  # ✅ CAMBIADO
            condiciones.append('Hemorragias')
        if obj.enfermedad_cardiaca != 'NO':
            condiciones.append('Cardíaca')
        if obj.vih_sida not in ['NEGATIVO', 'NO_SABE']:
            condiciones.append('VIH/SIDA')
        
        if condiciones:
            return format_html(
                '<span style="color: red; font-weight: bold;">{}</span>', 
                ', '.join(condiciones)
            )
        return 'Sin críticas'
    get_condiciones_criticas_display.short_description = 'Condiciones Críticas'
    
    def resumen_condiciones_display(self, obj):
        """Muestra resumen de condiciones en admin"""
        return format_html(
            '<div style="background-color: #f5f5f5; padding: 10px; border-radius: 5px;">{}</div>', 
            obj.resumen_condiciones
        )
    resumen_condiciones_display.short_description = 'Resumen de Condiciones'
    
    def get_queryset(self, request):
        """Optimizar consultas"""
        qs = super().get_queryset(request)
        return qs.select_related(
            'paciente', 
            'creado_por', 
            'actualizado_por'
        )
    
    def save_model(self, request, obj, form, change):
        """Asignar usuario que crea/modifica"""
        if not change:
            obj.creado_por = request.user
        obj.actualizado_por = request.user
        super().save_model(request, obj, form, change)
    
    # ✅ Acciones personalizadas
    actions = ['marcar_como_inactivo']
    
    @admin.action(description='📋 Marcar como inactivo')
    def marcar_como_inactivo(self, request, queryset):
        """Marcar anamnesis seleccionadas como inactivas"""
        updated = queryset.update(activo=False)
        self.message_user(
            request,
            f'{updated} anamnesis marcadas como inactivas',
            level='success'
        )