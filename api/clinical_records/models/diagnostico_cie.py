# api/clinical_records/models/diagnostico_cie.py
import uuid
from django.db import models


class DiagnosticoCIEHistorial(models.Model):
    """Almacena los diagnósticos CIE-10 asociados a un historial clínico específico"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Relación con el historial clínico
    historial_clinico = models.ForeignKey(
        'clinical_records.ClinicalRecord',
        on_delete=models.CASCADE,
        related_name='diagnosticos_cie',
        verbose_name='Historial Clínico'
    )

    # Relación con el diagnóstico dental original
    diagnostico_dental = models.ForeignKey(
        'odontogram.DiagnosticoDental',
        on_delete=models.PROTECT,
        related_name='en_historiales_clinicos',
        verbose_name='Diagnóstico Dental'
    )

    # Tipo de diagnóstico en este historial
    class TipoCIE(models.TextChoices):
        PRESUNTIVO = 'PRE', 'Presuntivo'
        DEFINITIVO = 'DEF', 'Definitivo'

    tipo_cie = models.CharField(
        max_length=3,
        choices=TipoCIE.choices,
        default=TipoCIE.PRESUNTIVO,
        verbose_name='Tipo CIE'
    )

    # -----------------------------------------------------------------------
    # Si está vacío, se usa el código del catálogo (comportamiento anterior).
    # Solo editable mientras el historial está en estado BORRADOR o ABIERTO.
    # -----------------------------------------------------------------------
    codigo_cie_personalizado = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='Código CIE-10 personalizado',
        help_text=(
            'Permite al profesional adaptar el código CIE-10 '
            '(ej. K08.1). Si se deja en blanco se usa el código del catálogo.'
        )
    )

    # Gestión individual
    activo = models.BooleanField(default=True, verbose_name='Activo')

    # Metadata
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    creado_por = models.ForeignKey(
        'users.Usuario',
        on_delete=models.PROTECT,
        related_name='diagnosticos_cie_creados',
        verbose_name='Creado por'
    )
    actualizado_por = models.ForeignKey(
        'users.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='diagnosticos_cie_actualizados',
        verbose_name='Actualizado por'
    )

    class Meta:
        db_table = 'clinical_diagnostico_cie_historial'
        verbose_name = 'Diagnóstico CIE en Historial'
        verbose_name_plural = 'Diagnósticos CIE en Historial'
        unique_together = ['historial_clinico', 'diagnostico_dental']
        indexes = [
            models.Index(fields=['historial_clinico', 'tipo_cie', 'activo']),
            models.Index(fields=['fecha_creacion']),
            models.Index(fields=['activo']),
        ]

    def __str__(self):
        return (
            f"{self.diagnostico_dental.diagnostico_catalogo.nombre} "
            f"[{self.codigo_cie_efectivo}] - {self.get_tipo_cie_display()}"
        )

    def delete(self, *args, **kwargs):
        """Eliminación lógica"""
        self.activo = False
        self.save()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def codigo_cie_efectivo(self):
        """
        Devuelve el código CIE-10 que debe usarse en la HC.
        Si el profesional ingresó un código personalizado, ese tiene prioridad.
        De lo contrario se usa el del catálogo.
        """
        if self.codigo_cie_personalizado and self.codigo_cie_personalizado.strip():
            return self.codigo_cie_personalizado.strip().upper()
        return self.diagnostico_dental.diagnostico_catalogo.codigo_icd10

    @property
    def codigo_cie(self):
        """
        Alias de compatibilidad hacia atrás.
        Devuelve el código efectivo (personalizado si existe, o del catálogo).
        """
        return self.codigo_cie_efectivo

    @property
    def codigo_cie_original(self):
        """Acceso al código CIE-10 original del catálogo (inmutable)."""
        return self.diagnostico_dental.diagnostico_catalogo.codigo_icd10

    @property
    def tiene_codigo_personalizado(self):
        """Indica si el profesional personalizó el código CIE-10."""
        return bool(
            self.codigo_cie_personalizado
            and self.codigo_cie_personalizado.strip()
        )

    @property
    def nombre_diagnostico(self):
        """Acceso rápido al nombre del diagnóstico"""
        return self.diagnostico_dental.diagnostico_catalogo.nombre

    @property
    def diente_fdi(self):
        """Acceso rápido al diente FDI"""
        if (
            self.diagnostico_dental.superficie
            and self.diagnostico_dental.superficie.diente
        ):
            return self.diagnostico_dental.superficie.diente.codigo_fdi
        return ""

    @property
    def superficie_nombre(self):
        """Acceso rápido al nombre de la superficie"""
        if self.diagnostico_dental.superficie:
            return self.diagnostico_dental.superficie.get_nombre_display()
        return ""