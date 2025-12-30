# patients/models/antecedentes_personales.py
from django.db import models
from .base import BaseModel
from .paciente import Paciente
from .constants import (
    ALERGIA_ANTIBIOTICO_CHOICES, ALERGIA_ANESTESIA_CHOICES,
    HEMORRAGIAS_CHOICES, VIH_SIDA_CHOICES,
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
        choices=ALERGIA_ANTIBIOTICO_CHOICES,
        default='NO',
        verbose_name="Alergia a antibiótico"
    )
    
    # 2. ALERGIA ANESTESIA
    alergia_anestesia = models.CharField(
        max_length=20,
        choices=ALERGIA_ANESTESIA_CHOICES,
        default='NO',
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
        max_length=25, 
        choices=VIH_SIDA_CHOICES,
        default='NEGATIVO',
        verbose_name="VIH/SIDA"
    )
    
    # 5. TUBERCULOSIS
    tuberculosis = models.CharField(
        max_length=25,  
        choices=TUBERCULOSIS_CHOICES,
        default='NUNCA',
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
        max_length=20,  
        choices=HIPERTENSION_CHOICES,
        default='NO',
        verbose_name="Hipertensión arterial"
    )
    
    # 9. ENFERMEDAD CARDIACA
    enfermedad_cardiaca = models.CharField(
        max_length=20,
        choices=ENFERMEDAD_CARDIACA_CHOICES,
        default='NO',
        verbose_name="Enfermedad cardíaca"
    )
    
      # 10. Campos extras
    alergia_antibiotico_otro = models.CharField(
        max_length=100, blank=True, null=True,
        verbose_name="Detalle alergia antibiótico",
        help_text="Amoxicilina, Cefalexina, etc."
    )
    
    alergia_anestesia_otro = models.CharField(
        max_length=100, blank=True, null=True,
        verbose_name="Detalle alergia anestesia",
        help_text="Lidocaína, Bupivacaína, etc."
    )
    
    enfermedad_cardiaca_otro = models.CharField(
        max_length=100, blank=True, null=True,
        verbose_name="Detalle enfermedad cardíaca",
        help_text="Arritmia auricular, valvulopatía, etc."
    )
    
    diabetes_otro = models.CharField(
        max_length=100, blank=True, null=True,
        verbose_name="Detalle diabetes",
        help_text="MODY, LADA, diabetes gestacional, etc."
    )

    
    class Meta:
        verbose_name = "Antecedente Personal"
        verbose_name_plural = "Antecedentes Personales"
        ordering = ['paciente__apellidos', 'paciente__nombres']
    
    def __str__(self):
        return f"Antecedentes personales de {self.paciente.nombre_completo}"
    
    @property
    def lista_antecedentes(self):
        """Retorna lista de antecedentes personales activos"""
        antecedentes = []
        
        # Alergias - solo si NO es "NO"
        if self.alergia_antibiotico != 'NO':
            antecedentes.append(f"Alergia antibiótico: {self.get_alergia_antibiotico_display()}")
        
        if self.alergia_anestesia != 'NO':
            antecedentes.append(f"Alergia anestesia: {self.get_alergia_anestesia_display()}")
        
        # Hemorragias - solo SI
        if self.hemorragias == 'SI':
            antecedentes.append("Hemorragias")
        
        # VIH/SIDA - solo POSITIVO
        if self.vih_sida == 'POSITIVO':
            antecedentes.append("VIH/SIDA: Positivo")
        
        # Tuberculosis - ACTIVA o TRATADA
        if self.tuberculosis in ['ACTIVA', 'TRATADA']:
            antecedentes.append(f"Tuberculosis: {self.get_tuberculosis_display()}")
        
        # Asma - solo si NO es "NO"
        if self.asma != 'NO':
            antecedentes.append(f"Asma: {self.get_asma_display()}")
        
        # Diabetes - solo si NO es "NO"
        if self.diabetes != 'NO':
            antecedentes.append(f"Diabetes: {self.get_diabetes_display()}")
        
        # Hipertensión - solo si NO es "NO"
        if self.hipertension_arterial != 'NO':
            antecedentes.append(f"Hipertensión: {self.get_hipertension_arterial_display()}")
        
        # Enfermedad cardíaca - solo si NO es "NO"
        if self.enfermedad_cardiaca != 'NO':
            antecedentes.append(f"Enfermedad cardíaca: {self.get_enfermedad_cardiaca_display()}")
        
        # Otros antecedentes
        if self.otros_antecedentes_personales.strip():
            otros = self.otros_antecedentes_personales.strip()
            otros_texto = otros[:50] + '...' if len(otros) > 50 else otros
            antecedentes.append(f"Otros: {otros_texto}")
        
        return antecedentes
    
    @property
    def tiene_antecedentes_criticos(self):
        """Indica si el paciente tiene antecedentes que requieren atención especial"""
        return (
            self.hemorragias == 'SI' or
            self.vih_sida == 'POSITIVO' or
            self.tuberculosis == 'ACTIVA' or
            self.asma == 'SEVERA' or
            self.diabetes in ['TIPO_1', 'TIPO_2'] or
            self.hipertension_arterial in ['NO_CONTROLADA', 'SIN_TRATAMIENTO'] or
            self.enfermedad_cardiaca != 'NO'
        )
    
    @property
    def tiene_alergias(self):
        """Indica si el paciente tiene alguna alergia registrada"""
        return (
            self.alergia_antibiotico != 'NO' or
            self.alergia_anestesia != 'NO'
        )
    
    @property
    def resumen_alergias(self):
        """Retorna un resumen de las alergias del paciente"""
        alergias = []
        if self.alergia_antibiotico != 'NO':
            alergias.append(self.get_alergia_antibiotico_display())
        if self.alergia_anestesia != 'NO':
            alergias.append(self.get_alergia_anestesia_display())
        return ', '.join(alergias) if alergias else 'Sin alergias'
    
    @property
    def total_antecedentes(self):
        """Cuenta el total de antecedentes positivos"""
        return len(self.lista_antecedentes)
    
    @property
    def riesgo_visual(self):
        """Retorna emoji de riesgo para mostrar en tablas"""
        if self.tiene_antecedentes_criticos:
            return "🚨"
        elif self.total_antecedentes > 2:
            return "⚠️"
        elif self.total_antecedentes > 0:
            return "ℹ️"
        return "✅"
