# odontogram/models.py
"""
Sistema completo de Odontograma con Catálogo Extensible + Registro de Instancias
Estructura:
- Catálogo: CategoriaDiagnostico, Diagnostico, TipoAtributoClinico, OpcionAtributoClinico
- Instancias: Diente, SuperficieDental, DiagnosticoDental, HistorialOdontograma
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

from api.patients.models import Paciente
from api.odontogram.constants import FDI_CHOICES, FDIConstants
from api.odontogram.validators.validator_fdi import validar_codigo_fdi


User = get_user_model()

# =============================================================================
# PARTE 1: CATÁLOGO DE DIAGNÓSTICOS (Lo que ya existe - SIN CAMBIOS)
# =============================================================================

class CategoriaDiagnostico(models.Model):
    """Categorías de diagnósticos disponibles"""
    key = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=100)
    color_key = models.CharField(max_length=7)
    prioridad_key = models.CharField(max_length=50)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'odonto_categoria_diagnostico'
        verbose_name = 'Categoría de Diagnóstico'
        verbose_name_plural = 'Categorías de Diagnóstico'

    def __str__(self):
        return self.nombre


class Diagnostico(models.Model):
    """Diagnósticos disponibles en el catálogo"""
    key = models.CharField(max_length=50, unique=True) 
    categoria = models.ForeignKey(CategoriaDiagnostico, on_delete=models.PROTECT, related_name='diagnosticos')
    nombre = models.CharField(max_length=100)
    siglas = models.CharField(max_length=10, blank=True)
    simbolo_color = models.CharField(max_length=50)
    prioridad = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    # Codigos Estandarizados 
    codigo_icd10 = models.CharField(max_length=20, blank=True, help_text="Código ICD-10 asociado")
    codigo_cdt = models.CharField(max_length=20, blank=True, help_text="Código CDT asociado")
    codigo_fhir = models.CharField(max_length=20, blank=True, help_text="Código SNOMED CT FHIR asociado")

    # Clasificación para serialización FHIR
    class TipoRecursoFHIR(models.TextChoices):
        CONDITION = 'Condition', 'Condición (Diagnóstico)'
        PROCEDURE = 'Procedure', 'Procedimiento (Tratamiento)'
        OBSERVATION = 'Observation', 'Observación (Otro hallazgo)'

    tipo_recurso_fhir = models.CharField(
        max_length=20,
        choices=TipoRecursoFHIR.choices,
        default=TipoRecursoFHIR.CONDITION,
        help_text="Clasifica el registro para su correcta serialización a FHIR (Condition, Procedure, etc.)"
    )

    # Simbologia formulario 033 Ecuador
    simbolo_formulario_033 = models.CharField(max_length=50, blank=True, choices=[('X_rojo', 'X rojo - Caries'), ('X_azul', 'X azul - Pérdida por caries'),
            ('_rojo', '| rojo - Caries necesaria (otra causa)'),
            ('U_rojo', 'Ü rojo - Sellante necesario'),
            ('U_azul', 'Ü azul - Sellante realizado'),
            ('r', 'r - Endodoncia por realizar'),
            ('_azul', '| azul - Endodoncia realizada'),
            ('o_azul', 'o azul - Obturado'),
            ('A', 'A - Ausente'),
            ('--', '¨---¨ - Prótesis fija indicada'),
            ('--_azul', '¨---¨ azul - Prótesis fija realizada'),
            ('-----', '(-----) - Prótesis removible indicada'),
            ('----_azul', '(-----) azul - Prótesis removible realizada'),
            ('ª', 'ª - Corona indicada'),
            ('ª_azul', 'ª azul - Corona realizada'),
            ('═', '═ - Prótesis total indicada'),
            ('═_azul', '═ azul - Prótesis total realizada'),])
    
    # Categoria de superficie aplicable
    superficie_aplicables = models.JSONField(
        default=list,
        blank=True,
        help_text="Lista de categorías de superficie dental aplicables (ej: ['oclusal', 'vestibular'])"
    )

    class Meta:
        db_table = 'odonto_diagnostico'
        verbose_name = 'Diagnóstico'
        verbose_name_plural = 'Diagnósticos'

    def __str__(self):
        return f"{self.siglas} - {self.nombre}"


class AreaAfectada(models.Model):
    """Áreas anatómicas del diente"""
    key = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=100)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'odonto_area_afectada'
        verbose_name = 'Área Afectada'
        verbose_name_plural = 'Áreas Afectadas'

    def __str__(self):
        return self.nombre


class DiagnosticoAreaAfectada(models.Model):
    """M2M: Diagnóstico -> AreaAfectada"""
    diagnostico = models.ForeignKey(Diagnostico, on_delete=models.CASCADE, related_name='areas_relacionadas')
    area = models.ForeignKey(AreaAfectada, on_delete=models.CASCADE, related_name='diagnosticos_relacionados')

    class Meta:
        db_table = 'odonto_diagnostico_area'
        unique_together = ['diagnostico', 'area']

    def __str__(self):
        return f"{self.diagnostico.siglas} → {self.area.nombre}"


class TipoAtributoClinico(models.Model):
    """Tipos de atributos clínicos disponibles"""
    key = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'odonto_tipo_atributo_clinico'
        verbose_name = 'Tipo de Atributo Clínico'
        verbose_name_plural = 'Tipos de Atributos Clínicos'

    def __str__(self):
        return self.nombre


class OpcionAtributoClinico(models.Model):
    """Opciones de atributos clínicos"""
    tipo_atributo = models.ForeignKey(TipoAtributoClinico, on_delete=models.CASCADE, related_name='opciones')
    key = models.CharField(max_length=50)
    nombre = models.CharField(max_length=100)
    prioridad = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    orden = models.IntegerField(default=0)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'odonto_opcion_atributo_clinico'
        verbose_name = 'Opción de Atributo Clínico'
        verbose_name_plural = 'Opciones de Atributos Clínicos'
        unique_together = ['tipo_atributo', 'key']

    def __str__(self):
        return f"{self.tipo_atributo.nombre}: {self.nombre}"


class DiagnosticoAtributoClinico(models.Model):
    """M2M: Diagnóstico -> TipoAtributoClinico"""
    diagnostico = models.ForeignKey(Diagnostico, on_delete=models.CASCADE, related_name='atributos_aplicables')
    tipo_atributo = models.ForeignKey(TipoAtributoClinico, on_delete=models.CASCADE, related_name='diagnosticos_aplicables')

    class Meta:
        db_table = 'odonto_diagnostico_atributo'
        unique_together = ['diagnostico', 'tipo_atributo']

    def __str__(self):
        return f"{self.diagnostico.siglas} → {self.tipo_atributo.nombre}"


# =============================================================================
# PARTE 2: ESTRUCTURA DE INSTANCIAS (PACIENTE -> DIENTE -> SUPERFICIE -> DIAGNÓSTICO)
# =============================================================================


class Diente(models.Model):
    """
    Registro de diente de un paciente
    Estructura jerárquica: Paciente -> Diente -> SuperficieDental -> DiagnosticoDental
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    paciente = models.ForeignKey(Paciente, on_delete=models.CASCADE, related_name='dientes')

    # Notación FDI (Fédération Dentaire Internationale)
    # Rango: 11-18 (superiores derechos), 21-28 (superiores izq),
    #        31-38 (inferiores izq), 41-48 (inferiores derechos)
    codigo_fdi = models.CharField(
        max_length=2,
        choices=FDI_CHOICES,  
        validators=[validar_codigo_fdi], 
        help_text="Código FDI internacional (11-48 permanentes, 51-85 temporales)"
    )
    # Información del diente
    nombre = models.CharField(
        max_length=100,
        blank=True,
        help_text="Nombre descriptivo (se genera automáticamente si está vacío)"
    )
    
    numero_3d = models.IntegerField(
        null=True,
        blank=True,
        editable=False,
        help_text="Número 3D del diente (1-52), auto-derivado desde FDI"
    )
    
    # Tipo de dentición
    tipo_denticion = models.CharField(
        max_length=20,
        choices=[
            ('permanente', 'Permanente'),
            ('temporal', 'Temporal'),
        ],
        editable=False,  # ← Auto-generado en save()
        default='permanente',
        help_text="Detectado automáticamente según código FDI (11-48 = permanente, 51-85 = temporal)"
    )
    
    ausente = models.BooleanField(
        default=False,
        help_text="Marca si el diente está ausente/extraccionado"
    )

    razon_ausencia = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('caries', 'Pérdida por caries'),
            ('otra_causa', 'Pérdida por otra causa'),
            ('sin_erupcionar', 'Sin erupcionar'),
            ('exodoncia_planificada', 'Extracción planificada'),
        ],
        help_text="Motivo de ausencia si ausente=True"
    )
    
    
    # Atributos clínicos
    movilidad = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(3)],
        help_text="Grados de movilidad (0-3) - Formulario 033"
    )
    
    recesion_gingival = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(4)],
        help_text="Recesión gingival en mm (0-4) - Formulario 033"
    )

    
    # Metadata
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        # Garantiza que no haya duplicados
        unique_together = ('paciente', 'codigo_fdi')
        ordering = ['codigo_fdi']
    
    def save(self, *args, **kwargs):
        """
            Override save para auto-generar campos derivados
            Garantiza que codigo_fdi sea el identificador único de cada diente
        """
    # Auto-generar nombre si no existe
        if not self.nombre:
            info = FDIConstants.obtener_info_fdi(self.codigo_fdi)
            if info:
                self.nombre = f"{info['nombre']} {info['arcada']}"
        
        # Auto-asignar numero_3d desde FDI (nunca cambiar)
        self.numero_3d = FDIConstants.FDI_A_NUMERO_3D.get(self.codigo_fdi)
    

    
    # Validar que si ausente=False, razon_ausencia esté vacía
        if not self.ausente:
            self.razon_ausencia = ''
    
        super().save(*args, **kwargs)

    def __str__(self):
        estado = " (AUSENTE)" if self.ausente else ""
        info = FDIConstants.obtener_info_fdi(self.codigo_fdi)
        if info:
            return f"FDI {self.codigo_fdi} - {info['nombre']}{estado}"
        return f"FDI {self.codigo_fdi}{estado}"
    
    
    @property
    def posicion_arcada(self):
        """SUPERIOR o INFERIOR (auto-derivado)"""
        info = FDIConstants.obtener_info_fdi(self.codigo_fdi)
        return info['arcada'] if info else None
    
    @property
    def posicion_cuadrante(self):
        """Cuadrante FDI (1-8) (auto-derivado)"""
        info = FDIConstants.obtener_info_fdi(self.codigo_fdi)
        return info['cuadrante'] if info else None
    
    @property
    def es_temporal(self):
        """True si es diente temporal (auto-derivado)"""
        info = FDIConstants.obtener_info_fdi(self.codigo_fdi)
        return info['denticion'] == 'temporal' if info else False
    
    @property
    def lado_arcada(self):
        """DERECHO o IZQUIERDO (auto-derivado)"""
        info = FDIConstants.obtener_info_fdi(self.codigo_fdi)
        return info['lado'] if info else None
    
    @property
    def tipo_denticion(self):
        """permanente o temporal (auto-derivado)"""
        info = FDIConstants.obtener_info_fdi(self.codigo_fdi)
        return info['denticion'] if info else None
    
    @property
    def info_completa(self):
        """Retorna toda la información del diente de forma estructurada"""
        return FDIConstants.obtener_info_fdi(self.codigo_fdi)


class SuperficieDental(models.Model):
    """
    Superficie específica de un diente de un paciente
    Ej: "vestibular" del diente 11 del paciente X
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    diente = models.ForeignKey(Diente, on_delete=models.CASCADE, related_name='superficies')

    # Tipo de superficie
    class TipoSuperficie(models.TextChoices):
        VESTIBULAR = 'vestibular', 'Vestibular'
        LINGUAL = 'lingual', 'Lingual/Palatina'
        OCLUSAL = 'oclusal', 'Oclusal/Incisal'
        MESIAL = 'mesial', 'Mesial'
        DISTAL = 'distal', 'Distal'
        # Raíces
        RAIZ_MESIAL = 'raiz_mesial', 'Raíz Mesial'
        RAIZ_DISTAL = 'raiz_distal', 'Raíz Distal'
        RAIZ_PALATAL = 'raiz_palatal', 'Raíz Palatina'
        RAIZ_VESTIBULAR = 'raiz_vestibular', 'Raíz Vestibular'
        RAIZ_PRINCIPAL = 'raiz_principal', 'Raíz Principal'
        
    # Mapeo de superficie a tipo
    SUPERFICIE_A_AREA = {
        # Superficies de Corona
        'vestibular': 'corona',
        'lingual': 'corona',
        'oclusal': 'corona',
        'mesial': 'corona',
        'distal': 'corona',
        
        # Raíces
        'raiz_mesial': 'raiz',
        'raiz_distal': 'raiz',
        'raiz_palatal': 'raiz',
        'raiz_vestibular': 'raiz',
        'raiz_principal': 'raiz',
    }
    # Mapeo de superficie a backend
    FRONTEND_ID_TO_BACKEND = {
        'cara_oclusal': 'oclusal',
        'cara_vestibular': 'vestibular',
        'cara_lingual': 'lingual',
        'cara_mesial': 'mesial',
        'cara_distal': 'distal',
        'raiz:raiz-mesial': 'raiz_mesial',
        'raiz:raiz-distal': 'raiz_distal',
        'raiz:raiz-palatal': 'raiz_palatal',
        'raiz:raiz-vestibular': 'raiz_vestibular',
        'raiz:raiz-principal': 'raiz_principal',
        'general': 'general',
    }

    nombre = models.CharField(max_length=50, choices=TipoSuperficie.choices)

    # Metadata
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    # Mapeo de superficies a codigos del FHIR/ADA
    FHIR_SURFACE_MAPPING = {
        'vestibular': 'F', # Facial/Buccal
        'lingual': 'L',    # Lingual
        'oclusal': 'O',    # Oclusal
        'incisal': 'I',   # Incisal
        'mesial': 'M',    # Mesial
        'distal': 'D',    # Distal
        'raiz_mesial': 'RM', # Raíz Mesial
        'raiz_distal': 'RD', # Raíz Distal
        'raiz_palatal': 'RP', # Raíz Palatina
        'raiz_vestibular': 'RV', # Raíz Vestibular
        'raiz_principal': 'RP', # Raíz Principal
    }

    codigo_fhir_superficie = models.CharField(
        max_length=2,
        null=True,  # ← Permitir nulo temporalmente
        blank=True,  # ← Permitir vacío en formularios
        editable=False,
        help_text="Código automático FHIR de la superficie dental")
    
    
    
    class Meta:
        db_table = 'odonto_superficie_dental'
        verbose_name = 'Superficie Dental'
        verbose_name_plural = 'Superficies Dentales'
        unique_together = ['diente', 'nombre']  # No duplicar superficies

    def __str__(self):
        return f"{self.diente.codigo_fdi} - {self.get_nombre_display()}"
    
    def save(self, *args, **kwargs):
        # Auto-mapear al guardar
        self.codigo_fhir_superficie = self.FHIR_SURFACE_MAPPING.get(self.nombre, self.nombre)
        super().save(*args, **kwargs)


class DiagnosticoDental(models.Model):
    """
    Diagnóstico registrado en una superficie específica de un diente
    Conecta con el catálogo de diagnósticos
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relaciones
    superficie = models.ForeignKey(SuperficieDental, on_delete=models.CASCADE, related_name='diagnosticos')
    diagnostico_catalogo = models.ForeignKey(
        Diagnostico,
        on_delete=models.PROTECT,
        related_name='instancias_aplicadas',
        help_text="Referencia al catálogo de diagnósticos"
    )
    odontologo = models.ForeignKey(User, on_delete=models.PROTECT, related_name='diagnosticos_registrados')

    # Datos del diagnóstico
    descripcion = models.TextField(
        blank=True,
        help_text="Descripción adicional o notas del odontólogo"
    )

    # Atributos clínicos seleccionados (JSON para flexibilidad)
    atributos_clinicos = models.JSONField(
        default=dict,
        blank=True,
        help_text="Opciones secundarias seleccionadas (ej: {material: 'resina', estado: 'buena'})"
    )

    # Prioridad personalizada (puede diferir del catálogo)
    prioridad_asignada = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Prioridad específica de este diagnóstico (si difiere del catálogo)"
    )
    movilidad = models.IntegerField(
        null=True,
        blank=True,
        choices=[(0, 'Sin movilidad'), (1, 'Movilidad 1'), (2, 'Movilidad 2'), (3, 'Movilidad 3'), (4, 'Movilidad 4')],
        help_text="Grado de movilidad dental (0-4) según Formulario 033"
    )
    recesion_gingival = models.IntegerField(
        null=True,
        blank=True,
        choices=[(0, 'Sin recesión'), (1, 'Recesión 1mm'), (2, 'Recesión 2mm'), (3, 'Recesión 3mm'), (4, 'Recesión >3mm')],
        help_text="Grado de recesión gingival según Formulario 033"
    )
    
    # Tipo de tratamiento (Para coloracion en formulario 033)
    tipo_registro = models.CharField(
        max_length=10,
        choices=[
            ('rojo', 'ROJO - Patología/hallazgo actual'),
            ('azul', 'AZUL - Tratamiento realizado previamente')
        ],
        default='rojo',
        help_text="Define la coloración en el Formulario 033"
    )
    
    
    # Estado del tratamiento
    class EstadoTratamiento(models.TextChoices):
        DIAGNOSTICADO = 'diagnosticado', 'Diagnosticado'
        EN_TRATAMIENTO = 'en_tratamiento', 'En Tratamiento'
        TRATADO = 'tratado', 'Tratado'
        CANCELADO = 'cancelado', 'Cancelado'

    estado_tratamiento = models.CharField(
        max_length=20,
        choices=EstadoTratamiento.choices,
        default=EstadoTratamiento.DIAGNOSTICADO
    )

    # Timestamps
    fecha = models.DateTimeField(auto_now_add=True, help_text="Fecha del diagnóstico")
    fecha_modificacion = models.DateTimeField(auto_now=True)
    fecha_tratamiento = models.DateTimeField(null=True, blank=True)

    # Control
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'odonto_diagnostico_dental'
        verbose_name = 'Diagnóstico Dental'
        verbose_name_plural = 'Diagnósticos Dentales'
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['superficie']),
            models.Index(fields=['estado_tratamiento']),
            models.Index(fields=['fecha']),
        ]

    def __str__(self):
        return f"{self.diagnostico_catalogo.siglas} - {self.superficie.diente.codigo_fdi} - {self.superficie.get_nombre_display()}"

    @property
    def prioridad_efectiva(self):
        """Retorna la prioridad asignada o la del catálogo"""
        return self.prioridad_asignada or self.diagnostico_catalogo.prioridad

    @property
    def diente(self):
        """Acceso rápido al diente"""
        return self.superficie.diente

    @property
    def paciente(self):
        """Acceso rápido al paciente"""
        return self.superficie.diente.paciente
    # Colores para renderización en formulario 033
    @property
    def color_hex(self):
        """Retorna el color hexadecimal según el tipo de registro (rojo/azul)"""
        # Mapeo desde tipo_registro
        mapeo_colores = {
            'rojo': '#FF0000',      # Rojo - Patología activa
            'azul': '#0000FF',      # Azul - Tratado
        }
        
        # Si existe estado_033, mapear desde allí
        if hasattr(self, 'estado_033') and self.estado_033:
            if 'azul' in str(self.estado_033):
                return '#0000FF'
            elif 'roja' in str(self.estado_033):
                return '#FF0000'
        
        # Fallback: usar tipo_registro
        return mapeo_colores.get(self.tipo_registro, '#CCCCCC')
    @property
    def priority(self):
        """
        Prioridad para renderización 3D
        CRÍTICO: Frontend lo usa para determinar color dominante
        Menor valor = Mayor prioridad de visualización
        """
        return self.diagnostico_catalogo.prioridad
    
    @property
    def area_anatomica(self):
        """
        Retorna el área anatómica de esta superficie
        Returns: 'corona', 'raiz', o 'general'
        """
        return self.SUPERFICIE_A_AREA.get(self.nombre, 'general')
    
    @classmethod
    def normalizar_superficie_frontend(cls, superficie_id_frontend):
        """
        Convierte ID del frontend a nombre backend
        """
        return cls.FRONTEND_ID_TO_BACKEND.get(
            superficie_id_frontend, 
            superficie_id_frontend
        )
    
    @classmethod
    def obtener_area_desde_frontend(cls, superficie_id_frontend):
        """
        Obtiene área anatómica directamente desde ID del frontend
        """
        nombre_backend = cls.normalizar_superficie_frontend(superficie_id_frontend)
        return cls.SUPERFICIE_A_AREA.get(nombre_backend, 'general')


class HistorialOdontograma(models.Model):
    """
    Registro histórico de cambios en el odontograma
    Auditoría: quién cambió qué y cuándo
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    diente = models.ForeignKey(Diente, on_delete=models.CASCADE, related_name='historial')

    class TipoCambio(models.TextChoices):
        DIAGNOSTICO_AGREGADO = 'diagnostico_agregado', 'Diagnóstico Agregado'
        DIAGNOSTICO_MODIFICADO = 'diagnostico_modificado', 'Diagnóstico Modificado'
        DIAGNOSTICO_ELIMINADO = 'diagnostico_eliminado', 'Diagnóstico Eliminado'
        DIAGNOSTICO_TRATADO = 'diagnostico_tratado', 'Diagnóstico Marcado como Tratado'
        DIENTE_MARCADO_AUSENTE = 'diente_marcado_ausente', 'Diente Marcado como Ausente'
        DIENTE_RESTAURADO = 'diente_restaurado', 'Diente Restaurado'
        NOTA_AGREGADA = 'nota_agregada', 'Nota Agregada'

    tipo_cambio = models.CharField(max_length=50, choices=TipoCambio.choices)
    descripcion = models.TextField(help_text="Descripción del cambio")

    # Quién lo hizo
    odontologo = models.ForeignKey(User, on_delete=models.PROTECT, related_name='cambios_odontograma')

    # Cuándo
    fecha = models.DateTimeField(auto_now_add=True)

    # Datos adicionales
    datos_anteriores = models.JSONField(default=dict, blank=True, help_text="Estado anterior (para auditoría)")
    datos_nuevos = models.JSONField(default=dict, blank=True, help_text="Estado nuevo (para auditoría)")

    class Meta:
        db_table = 'odonto_historial_odontograma'
        verbose_name = 'Historial Odontograma'
        verbose_name_plural = 'Historial Odontogramas'
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['diente']),
            models.Index(fields=['fecha']),
            models.Index(fields=['odontologo']),
        ]

    def __str__(self):
        return f"{self.get_tipo_cambio_display()} - {self.diente.codigo_fdi} - {self.fecha.strftime('%d/%m/%Y')}"
