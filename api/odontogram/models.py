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
    key = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=100)
    siglas = models.CharField(max_length=10, blank=True)
    simbolo_color = models.CharField(max_length=50)
    prioridad = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

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
        help_text="Código FDI del diente (ej: 11, 36, 48)"
    )
    nombre = models.CharField(
        max_length=100,
        blank=True,
        help_text="Nombre descriptivo opcional (ej: Primer molar inferior izquierdo)"
    )
    ausente = models.BooleanField(
        default=False,
        help_text="Marca si el diente está ausente/extraccionado"
    )

    # Metadata
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'odonto_diente'
        verbose_name = 'Diente'
        verbose_name_plural = 'Dientes'
        unique_together = ['paciente', 'codigo_fdi']  # Un paciente no puede tener dos "11"
        ordering = ['codigo_fdi']

    def __str__(self):
        estado = "(AUSENTE)" if self.ausente else ""
        paciente_nombre = f"{self.paciente.nombres} {self.paciente.apellidos}".strip()
        return f"Diente {self.codigo_fdi} - {paciente_nombre} {estado}".strip()


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

    nombre = models.CharField(max_length=50, choices=TipoSuperficie.choices)

    # Metadata
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'odonto_superficie_dental'
        verbose_name = 'Superficie Dental'
        verbose_name_plural = 'Superficies Dentales'
        unique_together = ['diente', 'nombre']  # No duplicar superficies

    def __str__(self):
        return f"{self.diente.codigo_fdi} - {self.get_nombre_display()}"


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