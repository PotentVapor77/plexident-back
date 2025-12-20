# patients/models/antecedentes_personales.py
from django.db import models
from .base import BaseModel
from .paciente import Paciente
from .constants import (
    ALERGIA_TIPO, HEMORRAGIAS_CHOICES, VIH_SIDA_CHOICES,
    TUBERCULOSIS_CHOICES, ASMA_CHOICES, DIABETES_CHOICES,
    HIPERTENSION_CHOICES, ENFERMEDAD_CARDIACA_CHOICES
)

class AntecedentesPersonales(BaseModel):
    """Antecedentes patológicos personales del paciente (Sección D)"""
    
    paciente = models.OneToOneField(
        Paciente,
        on_delete=models.CASCADE,
        related_name='antecedentes_personales',
        verbose_name="Paciente"
    )
    
    # 1. ALERGIA ANTIBIÓTICO
    alergia_antibiotico = models.CharField(
        max_length=20,
        choices=ALERGIA_TIPO,
        default='NINGUNA',
        verbose_name="Alergia a antibiótico"
    )
    
    # 2. ALERGIA ANESTESIA
    alergia_anestesia = models.CharField(
        max_length=20,
        choices=ALERGIA_TIPO,
        default='NINGUNA',
        verbose_name="Alergia a anestesia"
    )
    
    # 3. HEMORRAGIAS
    hemorragias = models.CharField(
        max_length=2,
        choices=HEMORRAGIAS_CHOICES,
        default='NO',
        verbose_name="Hemorragias"
    )
    
    # 4. VIH / SIDA
    vih_sida = models.CharField(
        max_length=10,
        choices=VIH_SIDA_CHOICES,
        default='NO_SABE',
        verbose_name="VIH/SIDA"
    )
    
    # 5. TUBERCULOSIS
    tuberculosis = models.CharField(
        max_length=10,
        choices=TUBERCULOSIS_CHOICES,
        default='NO_SABE',
        verbose_name="Tuberculosis"
    )
    
    # 6. ASMA
    asma = models.CharField(
        max_length=10,
        choices=ASMA_CHOICES,
        default='NO',
        verbose_name="Asma"
    )
    
    # 7. DIABETES
    diabetes = models.CharField(
        max_length=15,
        choices=DIABETES_CHOICES,
        default='NO',
        verbose_name="Diabetes"
    )
    
    # 8. HIPERTENSIÓN ARTERIAL
    hipertension_arterial = models.CharField(
        max_length=15,
        choices=HIPERTENSION_CHOICES,
        default='NO',
        verbose_name="Hipertensión arterial"
    )
    
    # 9. ENFERMEDAD CARDIACA
    enfermedad_cardiaca = models.CharField(
        max_length=10,
        choices=ENFERMEDAD_CARDIACA_CHOICES,
        default='NO',
        verbose_name="Enfermedad cardíaca"
    )
    
    # 10. OTRO
    otros_antecedentes_personales = models.TextField(blank=True, verbose_name="Otros antecedentes personales")
    
    class Meta:
        verbose_name = "Antecedentes Personales"
        verbose_name_plural = "Antecedentes Personales"
        ordering = ['paciente__apellidos', 'paciente__nombres']
    
    def __str__(self):
        return f"Antecedentes personales de {self.paciente.nombre_completo}"
    
    @property
    def lista_antecedentes(self):
        """Retorna lista de antecedentes personales activos"""
        antecedentes = []
        
        if self.alergia_antibiotico != 'NINGUNA':
            antecedentes.append(f"Alergia antibiótico: {self.get_alergia_antibiotico_display()}")
        
        if self.alergia_anestesia != 'NINGUNA':
            antecedentes.append(f"Alergia anestesia: {self.get_alergia_anestesia_display()}")
        
        if self.hemorragias == 'SI':
            antecedentes.append("Hemorragias")
        
        if self.vih_sida != 'NO_SABE':
            antecedentes.append(f"VIH/SIDA: {self.get_vih_sida_display()}")
        
        if self.tuberculosis != 'NO_SABE':
            antecedentes.append(f"Tuberculosis: {self.get_tuberculosis_display()}")
        
        if self.asma != 'NO':
            antecedentes.append(f"Asma: {self.get_asma_display()}")
        
        if self.diabetes != 'NO':
            antecedentes.append(f"Diabetes: {self.get_diabetes_display()}")
        
        if self.hipertension_arterial != 'NO':
            antecedentes.append(f"Hipertensión: {self.get_hipertension_arterial_display()}")
        
        if self.enfermedad_cardiaca != 'NO':
            antecedentes.append(f"Enfermedad cardíaca: {self.get_enfermedad_cardiaca_display()}")
        
        return antecedentes