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
        verbose_name="Temperatura (°C)",
        help_text="Rango normal: 35-42°C"
    )
    
    pulso = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        verbose_name="Pulso (/min)",
        help_text="Frecuencia cardíaca en latidos por minuto"
    )
    
    frecuencia_respiratoria = models.PositiveIntegerField(
        null=True, 
        blank=True, 
        verbose_name="Frecuencia respiratoria (/min)",
        help_text="Respiraciones por minuto"
    )
    
    presion_arterial = models.CharField(
        max_length=20,
        null=True, 
        blank=True, 
        verbose_name="Presión arterial (mmHg)",
        help_text="Formato: 120/80"
    )
    
    class Meta:
        verbose_name = "Constantes Vitales"
        verbose_name_plural = "Constantes Vitales"
        ordering = ['paciente__apellidos', 'paciente__nombres']
    
    def clean(self):
        """Validaciones del formulario"""
        # Validación: temperatura normal
        if self.temperatura and (self.temperatura < 35 or self.temperatura > 42):
            raise ValidationError({
                'temperatura': 'La temperatura debe estar entre 35°C y 42°C.'
            })
        
        # Validación: formato de presión arterial
        if self.presion_arterial:
            import re
            if not re.match(r'^\d{2,3}/\d{2,3}$', self.presion_arterial):
                raise ValidationError({
                    'presion_arterial': 'Formato inválido. Use formato: 120/80'
                })
    
    def __str__(self):
        return f"Constantes vitales de {self.paciente.nombre_completo}"
