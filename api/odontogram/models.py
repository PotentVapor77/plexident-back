# api/odontogram/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

"""Modelos para el sistema de odontogramas extensible."""

# 1. Categoria de Diagnostico

class CategoriaDiagnostico(models.Model):
    key = models.CharField(max_length=50, unique=True, help_text="Clave única para la categoría de diagnóstico.")
    nombre = models.CharField(max_length=100)
    color_key = models.CharField(max_length=50, help_text="Color en formato hexadecimal, e.g., #RRGGBB.")
    priodidad_key = models.CharField(max_length=50, help_text="Nivel de priodidad clinica: INFORMATIVA -> BAJA -> MEDIA -> ALTA -> ESTRUCTURAL.")
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'odonto_categoria_diagnostico'
        verbose_name = 'Categoría de Diagnóstico'
        verbose_name_plural = 'Categorías de Diagnóstico'
        ordering = ['nombre']
    def __str__(self) -> str:
        return self.nombre

# 2. Diagnostico

class Diagnostico(models.Model):
    """Diagnósticos dentales específicos (Caries, Fractura, Restauración etc.)"""
    categoria = models.ForeignKey(
        CategoriaDiagnostico,
        on_delete=models.PROTECT,
        related_name='diagnosticos'
    )
    key = models.CharField(
        max_length=50, 
        unique=True,
        help_text="Identificador único para el código"
    )
    nombre = models.CharField(max_length=100)
    siglas = models.CharField(max_length=10, blank=True)
    simbolo_color = models.CharField(
        max_length=50,
        help_text="Color del símbolo en el odontograma"
    )
    prioridad = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Nivel de prioridad clínica: 1 (baja) a 5 (crítica)"
    )
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'odonto_diagnostico'
        verbose_name = 'Diagnóstico'
        verbose_name_plural = 'Diagnósticos'
        ordering = ['categoria', 'nombre']

    def __str__(self):
        return f"{self.siglas} - {self.nombre}"
    
# 3. Area Afectada
class AreaAfectada(models.Model):
    """
    Áreas anatómicas del diente que pueden ser afectadas (ej: Corona, Raíz, General)
    """
    key = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=100)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'odonto_area_afectada'
        verbose_name = 'Área Afectada'
        verbose_name_plural = 'Áreas Afectadas'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


# 4. Diagnostico - Area Afectada (Relación M2M)
class DiagnosticoAreaAfectada(models.Model):
    """
    Relación muchos a muchos entre diagnósticos y áreas afectadas
    """
    diagnostico = models.ForeignKey(
        Diagnostico,
        on_delete=models.CASCADE,
        related_name='areas_relacionadas'
    )
    area = models.ForeignKey(
        AreaAfectada,
        on_delete=models.CASCADE,
        related_name='diagnosticos_relacionados'
    )

    class Meta:
        db_table = 'odonto_diagnostico_area'
        verbose_name = 'Diagnóstico - Área Afectada'
        verbose_name_plural = 'Diagnósticos - Áreas Afectadas'
        unique_together = ['diagnostico', 'area']

    def __str__(self):
        return f"{self.diagnostico.siglas} → {self.area.nombre}"
    

# 5. Tipo de atributo clinico
class TipoAtributoClinico(models.Model):
    """
    Tipos de atributos clínicos (ej: Material, Estado de Restauración, Movilidad)
    """
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
        ordering = ['nombre']

    def __str__(self):
        return self.nombre
    
# 6. Opcion de atributo clinico
class OpcionAtributoClinico(models.Model):
    """
    Opciones específicas para cada tipo de atributo clínico
    ( Material → Amalgama, Resina, Porcelana)
    """
    tipo_atributo = models.ForeignKey(
        TipoAtributoClinico,
        on_delete=models.CASCADE,
        related_name='opciones'
    )
    key = models.CharField(max_length=50)
    nombre = models.CharField(max_length=100)
    prioridad = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Nivel de prioridad clínica (1-5). NULL para atributos sin prioridad"
    )
    orden = models.IntegerField(
        default=0,
        help_text="Orden de visualización en la interfaz"
    )
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'odonto_opcion_atributo_clinico'
        verbose_name = 'Opción de Atributo Clínico'
        verbose_name_plural = 'Opciones de Atributos Clínicos'
        ordering = ['tipo_atributo', 'orden', 'nombre']
        unique_together = ['tipo_atributo', 'key']

    def __str__(self):
        return f"{self.tipo_atributo.nombre}: {self.nombre}"

# 7. Diagnostico - Tipo Atributo Clinico (Relación M2M)
class DiagnosticoAtributoClinico(models.Model):
    """
    Define qué tipos de atributos clínicos son aplicables a cada diagnóstico
    """
    diagnostico = models.ForeignKey(
        Diagnostico,
        on_delete=models.CASCADE,
        related_name='atributos_aplicables'
    )
    tipo_atributo = models.ForeignKey(
        TipoAtributoClinico,
        on_delete=models.CASCADE,
        related_name='diagnosticos_aplicables'
    )

    class Meta:
        db_table = 'odonto_diagnostico_atributo'
        verbose_name = 'Diagnóstico - Atributo Clínico'
        verbose_name_plural = 'Diagnósticos - Atributos Clínicos'
        unique_together = ['diagnostico', 'tipo_atributo']

    def __str__(self):
        return f"{self.diagnostico.siglas} → {self.tipo_atributo.nombre}"