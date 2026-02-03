# api/patients/admin.py
from django.contrib import admin
from django import forms  
from django.utils.html import format_html
from django.core.exceptions import ValidationError

from .models.examenes_complementarios import ExamenesComplementarios


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







@admin.register(AntecedentesPersonales)
class AntecedentesPersonalesAdmin(admin.ModelAdmin):
    """Admin para Antecedentes Personales"""
    
    list_display = [
        'paciente_info',
        'nivel_riesgo',
        'alergias_resumidas',
        'diabetes',
        'hipertension_arterial',
        'enfermedad_cardiaca',
        'tiene_condiciones_importantes',
        'fecha_creacion',
    ]
    
    list_filter = [
        'alergia_antibiotico',
        'alergia_anestesia',
        'hemorragias',
        'diabetes',
        'hipertension_arterial',
        'enfermedad_cardiaca',
        'asma',
        'vih_sida',
        'tuberculosis',
        'fecha_creacion',
    ]
    
    search_fields = [
        'paciente__nombres',
        'paciente__apellidos',
        'paciente__cedula_pasaporte',
        'paciente__numero_historia_clinica',
    ]
    
    readonly_fields = [
        'id',
        'fecha_creacion',
        'fecha_modificacion',
        'creado_por',
        'actualizado_por',
        'resumen_completo',
        'alergias_completas',
        'exigencias_quirurgicas_display',
    ]
    
    fieldsets = (
        ('Información del Paciente', {
            'fields': ('paciente', 'resumen_completo')
        }),
        ('Alergias', {
            'fields': (
                ('alergia_antibiotico', 'alergia_antibiotico_otro'),
                ('alergia_anestesia', 'alergia_anestesia_otro'),
                'alergias_completas',
            )
        }),
        ('Condiciones Médicas', {
            'fields': (
                ('hemorragias', 'hemorragias_detalle'),
                'vih_sida',
                'tuberculosis',
                'asma',
                ('diabetes', 'diabetes_otro'),
                'hipertension_arterial',
                ('enfermedad_cardiaca', 'enfermedad_cardiaca_otro'),
            )
        }),
        ('Otros Antecedentes', {
            'fields': (
                'otros_antecedentes_personales',
                'habitos',
                'observaciones',
            )
        }),
        ('Precauciones Quirúrgicas', {
            'fields': ('exigencias_quirurgicas_display',),
            'classes': ('collapse',)
        }),
        ('Metadatos', {
            'fields': (
                'id',
                'fecha_creacion',
                'fecha_modificacion',
                'creado_por',
                'actualizado_por',
            ),
            'classes': ('collapse',)
        }),
    )
    
    def paciente_info(self, obj):
        """Información del paciente con enlace"""
        url = f'/admin/patients/paciente/{obj.paciente.id}/change/'
        return format_html(
            '<a href="{}">{}</a><br><small>{}</small>',
            url,
            obj.paciente.nombre_completo,
            obj.paciente.cedula_pasaporte
        )
    paciente_info.short_description = 'Paciente'
    
    def nivel_riesgo(self, obj):
        """Nivel de riesgo con colores"""
        if obj.tiene_antecedentes_criticos:
            return format_html(
                '<span style="color: white; background-color: #dc3545; padding: 3px 8px; border-radius: 3px; font-weight: bold;">CRÍTICO</span>'
            )
        elif obj.total_antecedentes > 2:
            return format_html(
                '<span style="color: #856404; background-color: #fff3cd; padding: 3px 8px; border-radius: 3px; font-weight: bold;">ALTO</span>'
            )
        elif obj.total_antecedentes > 0:
            return format_html(
                '<span style="color: #0c5460; background-color: #d1ecf1; padding: 3px 8px; border-radius: 3px; font-weight: bold;">MEDIO</span>'
            )
        return format_html(
            '<span style="color: #155724; background-color: #d4edda; padding: 3px 8px; border-radius: 3px; font-weight: bold;">BAJO</span>'
        )
    nivel_riesgo.short_description = 'Riesgo'
    
    def alergias_resumidas(self, obj):
        """Resumen de alergias"""
        if obj.tiene_alergias:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">{}</span>',
                obj.resumen_alergias
            )
        return format_html('<span style="color: #28a745;">Sin alergias</span>')
    alergias_resumidas.short_description = 'Alergias'
    
    def resumen_completo(self, obj):
        """Resumen completo de condiciones"""
        if obj.tiene_condiciones_importantes:
            antecedentes = '<br>'.join([f'• {ant}' for ant in obj.lista_antecedentes])
            return format_html(
                '<div style="padding: 10px; background-color: #fff3cd; border-left: 4px solid #ffc107;">'
                '<strong>Condiciones importantes:</strong><br>{}</div>',
                antecedentes
            )
        return format_html(
            '<div style="padding: 10px; background-color: #d4edda; border-left: 4px solid #28a745;">'
            '<strong>Sin condiciones de riesgo</strong></div>'
        )
    resumen_completo.short_description = 'Resumen de Antecedentes'
    
    def alergias_completas(self, obj):
        """Detalle de alergias"""
        if not obj.tiene_alergias:
            return format_html('<span style="color: #28a745;">Sin alergias registradas</span>')
        
        alergias_list = []
        if obj.alergia_antibiotico != 'NO':
            texto = obj.get_alergia_antibiotico_display()
            if obj.alergia_antibiotico == 'OTRO' and obj.alergia_antibiotico_otro:
                texto += f' ({obj.alergia_antibiotico_otro})'
            alergias_list.append(f'<strong>Antibiótico:</strong> {texto}')
        
        if obj.alergia_anestesia != 'NO':
            texto = obj.get_alergia_anestesia_display()
            if obj.alergia_anestesia == 'OTRO' and obj.alergia_anestesia_otro:
                texto += f' ({obj.alergia_anestesia_otro})'
            alergias_list.append(f'<strong>Anestesia:</strong> {texto}')
        
        return format_html('<br>'.join(alergias_list))
    alergias_completas.short_description = 'Detalle de Alergias'
    
    def exigencias_quirurgicas_display(self, obj):
        """Mostrar exigencias quirúrgicas"""
        exigencias = obj.exigencias_quirurgicas
        if not exigencias:
            return format_html('<span style="color: #28a745;">Sin exigencias especiales</span>')
        
        items = '<br>'.join([f'• {ex}' for ex in exigencias])
        return format_html(
            '<div style="padding: 10px; background-color: #f8d7da; border-left: 4px solid #dc3545;">'
            '<strong>Precauciones:</strong><br>{}</div>',
            items
        )
    exigencias_quirurgicas_display.short_description = 'Exigencias Quirúrgicas'


@admin.register(AntecedentesFamiliares)
class AntecedentesFamiliaresAdmin(admin.ModelAdmin):
    """Admin para Antecedentes Familiares"""
    
    list_display = [
        'paciente_info',
        'cardiopatia_familiar',
        'hipertension_arterial_familiar',
        'cancer_familiar',
        'diabetes_familiar',
        'tiene_antecedentes_importantes',
        'fecha_creacion',
    ]
    
    list_filter = [
        'cardiopatia_familiar',
        'hipertension_arterial_familiar',
        'enfermedad_vascular_familiar',
        'cancer_familiar',
        'enfermedad_mental_familiar',
        'endocrino_metabolico_familiar',
        'tuberculosis_familiar',
        'fecha_creacion',
    ]
    
    search_fields = [
        'paciente__nombres',
        'paciente__apellidos',
        'paciente__cedula_pasaporte',
        'paciente__numero_historia_clinica',
    ]
    
    readonly_fields = [
        'id',
        'fecha_creacion',
        'fecha_modificacion',
        'creado_por',
        'actualizado_por',
        'resumen_antecedentes_display',
    ]
    
    fieldsets = (
        ('Información del Paciente', {
            'fields': ('paciente', 'resumen_antecedentes_display')
        }),
        ('Enfermedades Cardiovasculares', {
            'fields': (
                ('cardiopatia_familiar', 'cardiopatia_familiar_otro'),
                ('hipertension_arterial_familiar', 'hipertension_arterial_familiar_otro'),
                ('enfermedad_vascular_familiar', 'enfermedad_vascular_familiar_otro'),
            )
        }),
        ('Enfermedades Metabólicas y Cáncer', {
            'fields': (
                ('endocrino_metabolico_familiar', 'endocrino_metabolico_familiar_detalle'),
                ('cancer_familiar', 'cancer_familiar_otro'),
                ('tipo_cancer', 'tipo_cancer_otro'),
            )
        }),
        ('Enfermedades Infecciosas y Otras', {
            'fields': (
                ('tuberculosis_familiar', 'tuberculosis_familiar_detalle'),
                ('enfermedad_mental_familiar', 'enfermedad_mental_familiar_otro'),
                ('enfermedad_infecciosa_familiar', 'enfermedad_infecciosa_familiar_detalle'),
                ('malformacion_familiar', 'malformacion_familiar_detalle'),
            )
        }),
        ('Otros Antecedentes', {
            'fields': ('otros_antecedentes_familiares',)
        }),
        ('Metadatos', {
            'fields': (
                'id',
                'fecha_creacion',
                'fecha_modificacion',
                'creado_por',
                'actualizado_por',
            ),
            'classes': ('collapse',)
        }),
    )
    
    def paciente_info(self, obj):
        """Información del paciente con enlace"""
        url = f'/admin/patients/paciente/{obj.paciente.id}/change/'
        return format_html(
            '<a href="{}">{}</a><br><small>{}</small>',
            url,
            f"{obj.paciente.apellidos}, {obj.paciente.nombres}",
            obj.paciente.cedula_pasaporte
        )
    paciente_info.short_description = 'Paciente'
    
    def diabetes_familiar(self, obj):
        """Mostrar si tiene diabetes familiar"""
        if obj.endocrino_metabolico_familiar:
            return format_html('<span style="color: #856404;">SÍ</span>')
        return format_html('<span style="color: #6c757d;">NO</span>')
    diabetes_familiar.short_description = 'Diabetes'
    
    def resumen_antecedentes_display(self, obj):
        """Resumen de antecedentes familiares"""
        if not obj.tiene_antecedentes_importantes:
            return format_html(
                '<div style="padding: 10px; background-color: #d4edda; border-left: 4px solid #28a745;">'
                '<strong>Sin antecedentes familiares relevantes</strong></div>'
            )
        
        antecedentes = '<br>'.join([f'• {ant}' for ant in obj.lista_antecedentes])
        return format_html(
            '<div style="padding: 10px; background-color: #d1ecf1; border-left: 4px solid #17a2b8;">'
            '<strong>Antecedentes familiares:</strong><br>{}</div>',
            antecedentes
        )
    resumen_antecedentes_display.short_description = 'Resumen de Antecedentes'


@admin.register(ExamenesComplementarios)
class ExamenesComplementariosAdmin(admin.ModelAdmin):
    """Admin para Exámenes Complementarios"""
    
    list_display = [
        'paciente_info',
        'pedido_examenes',
        'informe_examenes',
        'estado_examenes_display',
        'fecha_creacion',
    ]
    
    list_filter = [
        'pedido_examenes',
        'informe_examenes',
        'fecha_creacion',
        'fecha_modificacion',
    ]
    
    search_fields = [
        'paciente__nombres',
        'paciente__apellidos',
        'paciente__cedula_pasaporte',
        'paciente__numero_historia_clinica',
        'pedido_examenes_detalle',
        'informe_examenes_detalle',
    ]
    
    readonly_fields = [
        'id',
        'fecha_creacion',
        'fecha_modificacion',
        'creado_por',
        'actualizado_por',
        'resumen_examenes_display',
    ]
    
    fieldsets = (
        ('Información del Paciente', {
            'fields': ('paciente', 'resumen_examenes_display')
        }),
        ('Pedido de Exámenes', {
            'fields': (
                'pedido_examenes',
                'pedido_examenes_detalle',
            )
        }),
        ('Informe de Exámenes', {
            'fields': (
                'informe_examenes',
                'informe_examenes_detalle',
            )
        }),
        ('Metadatos', {
            'fields': (
                'id',
                'fecha_creacion',
                'fecha_modificacion',
                'creado_por',
                'actualizado_por',
            ),
            'classes': ('collapse',)
        }),
    )
    
    def paciente_info(self, obj):
        """Información del paciente con enlace"""
        url = f'/admin/patients/paciente/{obj.paciente.id}/change/'
        return format_html(
            '<a href="{}">{}</a><br><small>{}</small>',
            url,
            obj.paciente.nombre_completo,
            obj.paciente.cedula_pasaporte
        )
    paciente_info.short_description = 'Paciente'
    
    def estado_examenes_display(self, obj):
        """Estado de exámenes con colores"""
        estado = obj.estado_examenes
        
        if estado == 'completado':
            return format_html(
                '<span style="color: white; background-color: #28a745; padding: 3px 8px; border-radius: 3px; font-weight: bold;">COMPLETADO</span>'
            )
        elif estado == 'pendiente':
            return format_html(
                '<span style="color: #856404; background-color: #fff3cd; padding: 3px 8px; border-radius: 3px; font-weight: bold;">PENDIENTE</span>'
            )
        else:
            return format_html(
                '<span style="color: #6c757d; background-color: #e9ecef; padding: 3px 8px; border-radius: 3px;">NO SOLICITADO</span>'
            )
    estado_examenes_display.short_description = 'Estado'
    
    def resumen_examenes_display(self, obj):
        """Resumen de exámenes complementarios"""
        estado = obj.estado_examenes
        
        if estado == 'completado':
            return format_html(
                '<div style="padding: 10px; background-color: #d4edda; border-left: 4px solid #28a745;">'
                '<strong>Estado:</strong> Completado<br>'
                '<strong>Tipo:</strong> {}<br>'
                '<strong>Resultado:</strong> {}</div>',
                obj.get_informe_examenes_display(),
                obj.informe_examenes_detalle[:100] + '...' if len(obj.informe_examenes_detalle) > 100 else obj.informe_examenes_detalle
            )
        elif estado == 'pendiente':
            return format_html(
                '<div style="padding: 10px; background-color: #fff3cd; border-left: 4px solid #ffc107;">'
                '<strong>Estado:</strong> Pendiente<br>'
                '<strong>Solicitados:</strong> {}</div>',
                obj.pedido_examenes_detalle[:100] + '...' if len(obj.pedido_examenes_detalle) > 100 else obj.pedido_examenes_detalle
            )
        else:
            return format_html(
                '<div style="padding: 10px; background-color: #e9ecef; border-left: 4px solid #6c757d;">'
                '<strong>No se han solicitado exámenes complementarios</strong></div>'
            )
    resumen_examenes_display.short_description = 'Resumen de Exámenes'