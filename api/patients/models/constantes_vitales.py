# patients/models/constantes_vitales.py
from django.db import models
from django.core.exceptions import ValidationError
from .base import BaseModel
from .paciente import Paciente

class ConstantesVitales(BaseModel):
    """Constantes vitales del paciente (Sección F)"""
    
    paciente = models.OneToOneField(
        Paciente,
        on_delete=models.CASCADE,
        related_name='constantes_vitales',
        verbose_name="Paciente"
    )
    
    temperatura = models.DecimalField(
        max_digits=4, 
        decimal_places=1, 
        null=True, 
        blank=True, 
        verbose_name="Temperatura (°C)"
    )
    
    pulso = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        verbose_name="Pulso (/min)"
    )
    
    frecuencia_respiratoria = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        verbose_name="Frecuencia respiratoria (/min)"
    )
    
    presion_arterial_sistolica = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        verbose_name="Presión arterial sistólica (mmHg)"
    )
    
    presion_arterial_diastolica = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        verbose_name="Presión arterial diastólica (mmHg)"
    )
    
    class Meta:
        verbose_name = "Constantes Vitales"
        verbose_name_plural = "Constantes Vitales"
        ordering = ['paciente__apellidos', 'paciente__nombres']
    
    def clean(self):
        """Validaciones del formulario"""
        # Validación: presión arterial
        if (self.presion_arterial_sistolica and not self.presion_arterial_diastolica) or \
           (not self.presion_arterial_sistolica and self.presion_arterial_diastolica):
            raise ValidationError("Debe especificar tanto la presión sistólica como diastólica.")
        
        # Validación: temperatura normal
        if self.temperatura and (self.temperatura < 35 or self.temperatura > 42):
            raise ValidationError("La temperatura debe estar entre 35°C y 42°C.")
    
    def __str__(self):
        return f"Constantes vitales de {self.paciente.nombre_completo}"
    
    @property
    def presion_arterial(self):
        """Retorna la presión arterial formateada"""
        if self.presion_arterial_sistolica and self.presion_arterial_diastolica:
            return f"{self.presion_arterial_sistolica}/{self.presion_arterial_diastolica} mmHg"
        return "No registrada"