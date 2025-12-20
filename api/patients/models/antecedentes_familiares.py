# patients/models/antecedentes_familiares.py
from django.db import models
from .base import BaseModel
from .paciente import Paciente
from .constants import (
    CARDIOPATIA_FAMILIAR_CHOICES, HIPERTENSION_FAMILIAR_CHOICES,
    ENFERMEDAD_VASCULAR_CHOICES, CANCER_FAMILIAR_CHOICES,
    ENFERMEDAD_MENTAL_CHOICES
)

class AntecedentesFamiliares(BaseModel):
    """Antecedentes patológicos familiares del paciente (Sección E)"""
    
    paciente = models.OneToOneField(
        Paciente,
        on_delete=models.CASCADE,
        related_name='antecedentes_familiares',
        verbose_name="Paciente"
    )
    
    # 1. CARDIOPATÍA
    cardiopatia_familiar = models.CharField(
        max_length=10,
        choices=CARDIOPATIA_FAMILIAR_CHOICES,
        default='NO',
        verbose_name="Cardiopatía familiar"
    )
    
    # 2. HIPERTENSIÓN ARTERIAL
    hipertension_arterial_familiar = models.CharField(
        max_length=10,
        choices=HIPERTENSION_FAMILIAR_CHOICES,
        default='NO',
        verbose_name="Hipertensión arterial familiar"
    )
    
    # 3. ENFERMEDAD C. VASCULAR
    enfermedad_vascular_familiar = models.CharField(
        max_length=10,
        choices=ENFERMEDAD_VASCULAR_CHOICES,
        default='NO',
        verbose_name="Enfermedad vascular familiar"
    )
    
    # 4. ENDÓCRINO METABÓLICO
    endocrino_metabolico_familiar = models.BooleanField(default=False, verbose_name="Endócrino metabólico familiar")
    
    # 5. CÁNCER
    cancer_familiar = models.CharField(
        max_length=10,
        choices=CANCER_FAMILIAR_CHOICES,
        default='NO',
        verbose_name="Cáncer familiar"
    )
    
    # 6. TUBERCULOSIS
    tuberculosis_familiar = models.BooleanField(default=False, verbose_name="Tuberculosis familiar")
    
    # 7. ENFERMEDAD MENTAL
    enfermedad_mental_familiar = models.CharField(
        max_length=10,
        choices=ENFERMEDAD_MENTAL_CHOICES,
        default='NO',
        verbose_name="Enfermedad mental familiar"
    )
    
    # 8. ENFERMEDAD INFECCIOSA
    enfermedad_infecciosa_familiar = models.BooleanField(default=False, verbose_name="Enfermedad infecciosa familiar")
    
    # 9. MALFORMACIÓN
    malformacion_familiar = models.BooleanField(default=False, verbose_name="Malformación familiar")
    
    # 10. OTRO
    otros_antecedentes_familiares = models.TextField(blank=True, verbose_name="Otros antecedentes familiares")
    
    class Meta:
        verbose_name = "Antecedentes Familiares"
        verbose_name_plural = "Antecedentes Familiares"
        ordering = ['paciente__apellidos', 'paciente__nombres']
    
    def __str__(self):
        return f"Antecedentes familiares de {self.paciente.nombre_completo}"
    
    @property
    def lista_antecedentes(self):
        """Retorna lista de antecedentes familiares activos"""
        antecedentes = []
        
        if self.cardiopatia_familiar != 'NO':
            antecedentes.append(f"Cardiopatía: {self.get_cardiopatia_familiar_display()}")
        
        if self.hipertension_arterial_familiar != 'NO':
            antecedentes.append(f"Hipertensión: {self.get_hipertension_arterial_familiar_display()}")
        
        if self.enfermedad_vascular_familiar != 'NO':
            antecedentes.append(f"Enf. vascular: {self.get_enfermedad_vascular_familiar_display()}")
        
        if self.endocrino_metabolico_familiar:
            antecedentes.append("Endócrino metabólico")
        
        if self.cancer_familiar != 'NO':
            antecedentes.append(f"Cáncer: {self.get_cancer_familiar_display()}")
        
        if self.tuberculosis_familiar:
            antecedentes.append("Tuberculosis")
        
        if self.enfermedad_mental_familiar != 'NO':
            antecedentes.append(f"Enf. mental: {self.get_enfermedad_mental_familiar_display()}")
        
        if self.enfermedad_infecciosa_familiar:
            antecedentes.append("Enfermedad infecciosa")
        
        if self.malformacion_familiar:
            antecedentes.append("Malformación")
        
        return antecedentes