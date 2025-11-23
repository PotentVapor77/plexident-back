# api/odontogram/admin.py

from django.contrib import admin
from .models import (
    CategoriaDiagnostico,
    Diagnostico,
    AreaAfectada,
    DiagnosticoAreaAfectada,
    TipoAtributoClinico,
    OpcionAtributoClinico,
    DiagnosticoAtributoClinico,
    Diente,
    SuperficieDental,
    DiagnosticoDental,
    HistorialOdontograma
)


# ============================================================================
# CATÁLOGO DE DIAGNÓSTICOS (LECTURA PRINCIPALMENTE)
# ============================================================================

admin.site.register(CategoriaDiagnostico)
admin.site.register(Diagnostico)
admin.site.register(AreaAfectada)
admin.site.register(DiagnosticoAreaAfectada)
admin.site.register(TipoAtributoClinico)
admin.site.register(OpcionAtributoClinico)
admin.site.register(DiagnosticoAtributoClinico)


# ============================================================================
# INSTANCIAS DE ODONTOGRAMAS (CON CASCADA)
# ============================================================================

# INLINE 1: Diagnósticos dentro de Superficie
class DiagnosticoDentalInline(admin.TabularInline):
    """Inline para ver diagnósticos de una superficie"""
    model = DiagnosticoDental
    extra = 1
    fields = (
        'diagnostico_catalogo',
        'estado_tratamiento',
        'prioridad_asignada',
        'fecha',
        'activo'
    )
    readonly_fields = ('fecha',)
    ordering = ['-fecha']


# INLINE 2: Superficies dentro de Diente
class SuperficieDentalInline(admin.TabularInline):
    """Inline para ver superficies de un diente"""
    model = SuperficieDental
    extra = 1
    fields = ('nombre', 'fecha_creacion')
    readonly_fields = ('fecha_creacion',)


# ADMIN 1: SuperficieDental (con inlines de diagnósticos)
class SuperficieDentalAdmin(admin.ModelAdmin):
    """Admin para superficies dentales con diagnósticos anidados"""
    list_display = (
        'diente_info',
        'nombre',
        'diagnosticos_count',
        'fecha_creacion'
    )
    search_fields = (
        'diente__codigo_fdi',
        'diente__paciente__nombres',
        'diente__paciente__apellidos'
    )
    list_filter = ('nombre', 'fecha_creacion')
    readonly_fields = ('fecha_creacion', 'fecha_modificacion')

    # Agregar inline de diagnósticos
    inlines = [DiagnosticoDentalInline]

    fieldsets = (
        ('Información', {
            'fields': ('diente', 'nombre')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )

    def diente_info(self, obj):
        """Muestra info del diente con paciente"""
        paciente = obj.diente.paciente
        return f"{obj.diente.codigo_fdi} ({paciente.nombres} {paciente.apellidos})"
    diente_info.short_description = 'Diente'

    def diagnosticos_count(self, obj):
        """Cuenta de diagnósticos en esta superficie"""
        return obj.diagnosticos.filter(activo=True).count()
    diagnosticos_count.short_description = 'Diagnósticos'


# ADMIN 2: Diente (con inlines de superficies y diagnósticos en cascada)
class DienteAdmin(admin.ModelAdmin):
    """Admin para dientes con superficies anidadas"""
    list_display = (
        'codigo_fdi',
        'paciente_info',
        'ausente',
        'superficies_count',
        'diagnosticos_count',
        'fecha_creacion'
    )
    search_fields = (
        'codigo_fdi',
        'paciente__nombres',
        'paciente__apellidos',
        'nombre'
    )
    list_filter = ('ausente', 'paciente', 'fecha_creacion')
    readonly_fields = ('fecha_creacion', 'fecha_modificacion')

    # Agregar inline de superficies (y estos a su vez tendrán diagnósticos)
    inlines = [SuperficieDentalInline]

    fieldsets = (
        ('Información del Diente', {
            'fields': ('paciente', 'codigo_fdi', 'nombre')
        }),
        ('Estado', {
            'fields': ('ausente',)
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
    )

    def paciente_info(self, obj):
        """Muestra nombre del paciente"""
        return f"{obj.paciente.nombres} {obj.paciente.apellidos}"
    paciente_info.short_description = 'Paciente'

    def superficies_count(self, obj):
        """Cuenta de superficies"""
        return obj.superficies.count()
    superficies_count.short_description = 'Superficies'

    def diagnosticos_count(self, obj):
        """Cuenta total de diagnósticos"""
        total = 0
        for superficie in obj.superficies.all():
            total += superficie.diagnosticos.filter(activo=True).count()
        return total
    diagnosticos_count.short_description = 'Total Diagnósticos'


# ADMIN 3: DiagnosticoDental (lectura con contexto)
class DiagnosticoDentalAdmin(admin.ModelAdmin):
    """Admin para diagnósticos dentales registrados"""
    list_display = (
        'diagnostico_nombre',
        'diente_info',
        'superficie_nombre',
        'estado_tratamiento',
        'prioridad_efectiva',
        'fecha'
    )
    search_fields = (
        'diagnostico_catalogo__nombre',
        'diagnostico_catalogo__siglas',
        'superficie__diente__codigo_fdi',
        'superficie__diente__paciente__nombres',
        'superficie__diente__paciente__apellidos'
    )
    list_filter = (
        'estado_tratamiento',
        'diagnostico_catalogo__categoria',
        'prioridad_asignada',
        'fecha'
    )
    readonly_fields = ('fecha', 'fecha_modificacion', 'prioridad_efectiva', 'paciente_info', 'diente_info_complete')

    fieldsets = (
        ('Información Clínica', {
            'fields': (
                'diagnostico_catalogo',
                'superficie',
                'paciente_info',
                'diente_info_complete',
                'odontologo'
            )
        }),
        ('Diagnóstico', {
            'fields': (
                'descripcion',
                'estado_tratamiento',
                'prioridad_asignada',
                'prioridad_efectiva',
                'atributos_clinicos'
            )
        }),
        ('Tratamiento', {
            'fields': ('fecha', 'fecha_tratamiento', 'fecha_modificacion'),
            'classes': ('collapse',)
        }),
        ('Control', {
            'fields': ('activo',),
            'classes': ('collapse',)
        }),
    )

    def diagnostico_nombre(self, obj):
        """Nombre del diagnóstico con siglas"""
        return f"{obj.diagnostico_catalogo.siglas} - {obj.diagnostico_catalogo.nombre}"
    diagnostico_nombre.short_description = 'Diagnóstico'

    def diente_info(self, obj):
        """Código del diente"""
        return obj.superficie.diente.codigo_fdi
    diente_info.short_description = 'Diente'

    def diente_info_complete(self, obj):
        """Info completa del diente (readonly)"""
        diente = obj.superficie.diente
        return f"Código FDI: {diente.codigo_fdi} | Nombre: {diente.nombre or 'N/A'}"
    diente_info_complete.short_description = 'Información del Diente'

    def paciente_info(self, obj):
        """Info del paciente (readonly)"""
        paciente = obj.paciente
        return f"{paciente.nombres} {paciente.apellidos} (ID: {paciente.id_paciente})"
    paciente_info.short_description = 'Paciente'

    def superficie_nombre(self, obj):
        """Nombre de la superficie"""
        return obj.superficie.get_nombre_display()
    superficie_nombre.short_description = 'Superficie'

    def prioridad_efectiva(self, obj):
        """Prioridad calculada"""
        return f"P{obj.prioridad_efectiva}"
    prioridad_efectiva.short_description = 'Prioridad'


# ADMIN 4: HistorialOdontograma (solo lectura)
class HistorialOdontogramaAdmin(admin.ModelAdmin):
    """Admin para historial de cambios"""
    list_display = (
        'tipo_cambio_display',
        'diente_info',
        'odontologo',
        'fecha',
        'descripcion_truncada'
    )
    search_fields = (
        'descripcion',
        'diente__codigo_fdi',
        'diente__paciente__nombres',
        'diente__paciente__apellidos'
    )
    list_filter = ('tipo_cambio', 'odontologo', 'fecha')
    readonly_fields = ('diente', 'tipo_cambio', 'descripcion', 'odontologo', 'fecha', 'datos_anteriores', 'datos_nuevos')

    fieldsets = (
        ('Información del Cambio', {
            'fields': ('fecha', 'tipo_cambio', 'diente', 'odontologo', 'descripcion')
        }),
        ('Datos Auditados', {
            'fields': ('datos_anteriores', 'datos_nuevos'),
            'classes': ('collapse',)
        }),
    )

    def tipo_cambio_display(self, obj):
        """Muestra el tipo de cambio"""
        return obj.get_tipo_cambio_display()
    tipo_cambio_display.short_description = 'Tipo'

    def diente_info(self, obj):
        """Info del diente"""
        paciente = obj.diente.paciente
        return f"{obj.diente.codigo_fdi} ({paciente.nombres} {paciente.apellidos})"
    diente_info.short_description = 'Diente'

    def descripcion_truncada(self, obj):
        """Descripción truncada"""
        return obj.descripcion[:50] + '...' if len(obj.descripcion) > 50 else obj.descripcion
    descripcion_truncada.short_description = 'Descripción'

    def has_add_permission(self, request):
        """El historial se genera automáticamente"""
        return False

    def has_change_permission(self, request, obj=None):
        """El historial no se modifica"""
        return False

    def has_delete_permission(self, request, obj=None):
        """El historial no se elimina"""
        return False


# Registrar admins
admin.site.register(Diente, DienteAdmin)
admin.site.register(SuperficieDental, SuperficieDentalAdmin)
admin.site.register(DiagnosticoDental, DiagnosticoDentalAdmin)
admin.site.register(HistorialOdontograma, HistorialOdontogramaAdmin)
