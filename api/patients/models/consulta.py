# api/patients/models/consulta.py

from django.db import models
from django.utils import timezone
from api.patients.models.paciente import Paciente
from api.patients.models.base import BaseModel


class Consulta(BaseModel):
    """Registro de consulta médica por visita del paciente"""
    
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name='consultas',
        help_text="Paciente asociado a la consulta"
    )
    
    # Datos específicos de esta consulta
    fecha_consulta = models.DateField(
        default=timezone.now,
        help_text="Fecha de la consulta"
    )
    motivo_consulta = models.TextField(
        help_text="Motivo o razón de la visita"
    )
    enfermedad_actual = models.TextField(
        help_text="Descripción detallada: síntomas, cronología, localización, intensidad"
    )
    
    # Campos adicionales opcionales
    diagnostico = models.TextField(
        blank=True,
        help_text="Diagnóstico médico realizado"
    )
    plan_tratamiento = models.TextField(
        blank=True,
        help_text="Plan de tratamiento propuesto"
    )
    observaciones = models.TextField(
        blank=True,
        help_text="Observaciones adicionales"
    )
    
    class Meta:
        db_table = 'consultas'
        ordering = ['-fecha_consulta', '-fecha_creacion']
        verbose_name = 'Consulta'
        verbose_name_plural = 'Consultas'
        indexes = [
            models.Index(fields=['paciente', '-fecha_consulta']),
            models.Index(fields=['activo']),
        ]
    
    def __str__(self):
        return f"Consulta - {self.paciente.nombre_completo} ({self.fecha_consulta})"
    
    @property
    def paciente_nombre(self):
        """Nombre completo del paciente"""
        return self.paciente.nombre_completo if self.paciente else "Sin paciente"
