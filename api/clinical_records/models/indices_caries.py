# api/patients/models/indices_caries.py
"""
Modelo para almacenar índices de caries (CPO/ceo) del paciente
"""

from django.db import models
from jsonschema import ValidationError
from api.patients.models.base import BaseModel
from api.patients.models.paciente import Paciente
from api.users.models import Usuario
from django.utils import timezone

class IndicesCaries(BaseModel):
    """
    Registro de índices de caries de un paciente en un momento específico
    Relacionado con snapshot del odontograma
    """
    
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name='indices_caries',
        verbose_name='Paciente'
    )
    
    # Referencia al snapshot del odontograma (opcional)
    version_odontograma = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="ID de versión del odontograma (HistorialOdontograma.version_id)"
    )
    
    # Fecha de evaluación
    fecha_evaluacion = models.DateTimeField(
        default=timezone.now,
        verbose_name='Fecha de evaluación'
    )
    
    # ===== ÍNDICES PARA DENTICIÓN PERMANENTE (CPO) =====
    cpo_c = models.PositiveIntegerField(
        default=0,
        verbose_name='Dientes permanentes cariados'
    )
    
    cpo_p = models.PositiveIntegerField(
        default=0,
        verbose_name='Dientes permanentes perdidos por caries'
    )
    
    cpo_o = models.PositiveIntegerField(
        default=0,
        verbose_name='Dientes permanentes obturados'
    )
    
    cpo_total = models.PositiveIntegerField(
        default=0,
        verbose_name='Índice CPO total'
    )
    
    # ===== ÍNDICES PARA DENTICIÓN TEMPORAL (ceo) =====
    ceo_c = models.PositiveIntegerField(
        default=0,
        verbose_name='Dientes temporales cariados'
    )
    
    ceo_e = models.PositiveIntegerField(
        default=0,
        verbose_name='Dientes temporales con extracción indicada'
    )
    
    ceo_o = models.PositiveIntegerField(
        default=0,
        verbose_name='Dientes temporales obturados'
    )
    
    ceo_total = models.PositiveIntegerField(
        default=0,
        verbose_name='Índice ceo total'
    )
    
    # ===== METADATA =====
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones del profesional'
    )
    
    creado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='indices_c_creados',
        verbose_name='Creado por'
    )
    
    # Auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Índices de Caries'
        verbose_name_plural = 'Índices de Caries'
        ordering = ['-fecha_evaluacion']
        indexes = [
            models.Index(fields=['paciente', '-fecha_evaluacion']),
            models.Index(fields=['activo']),
        ]
    
    def __str__(self):
        return f"CPO {self.cpo_total} / ceo {self.ceo_total} - {self.paciente.nombre_completo} - {self.fecha_evaluacion.date()}"
    
    def clean(self):
        """Validaciones del modelo"""
        super().clean()
        
        # Validar que los totales sean consistentes
        if self.cpo_total != (self.cpo_c + self.cpo_p + self.cpo_o):
            self.cpo_total = self.cpo_c + self.cpo_p + self.cpo_o
        
        if self.ceo_total != (self.ceo_c + self.ceo_e + self.ceo_o):
            self.ceo_total = self.ceo_c + self.ceo_e + self.ceo_o
        
        # Validar que el paciente exista
        if not self.paciente:
            raise ValidationError('El paciente es requerido')
    
    def save(self, *args, **kwargs):
        """Sobrescribe save para aplicar validaciones"""
        self.clean()
        super().save(*args, **kwargs)