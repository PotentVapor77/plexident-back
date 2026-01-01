# patients/models/antecedentes_familiares.py
from django.db import models
from .base import BaseModel
from .paciente import Paciente
from .constants import (
    CARDIOPATIA_FAMILIAR_CHOICES, 
    HIPERTENSION_FAMILIAR_CHOICES,
    ENFERMEDAD_VASCULAR_CHOICES, 
    CANCER_FAMILIAR_CHOICES,
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
        max_length=15,  # ✅ Aumentado
        choices=CARDIOPATIA_FAMILIAR_CHOICES,
        default='NO',
        verbose_name="Cardiopatía familiar"
    )
    
    # 2. HIPERTENSIÓN ARTERIAL
    hipertension_arterial_familiar = models.CharField(
        max_length=15,  # ✅ Aumentado
        choices=HIPERTENSION_FAMILIAR_CHOICES,
        default='NO',
        verbose_name="Hipertensión arterial familiar"
    )
    
    # 3. ENFERMEDAD C. VASCULAR
    enfermedad_vascular_familiar = models.CharField(
        max_length=15,  # ✅ Aumentado
        choices=ENFERMEDAD_VASCULAR_CHOICES,
        default='NO',
        verbose_name="Enfermedad vascular familiar"
    )
    
   
    # 5. CÁNCER
    cancer_familiar = models.CharField(
        max_length=15,  # ✅ Aumentado
        choices=CANCER_FAMILIAR_CHOICES,
        default='NO',
        verbose_name="Cáncer familiar"
    )
    

    # 7. ENFERMEDAD MENTAL
    enfermedad_mental_familiar = models.CharField(
        max_length=15,  # ✅ Aumentado
        choices=ENFERMEDAD_MENTAL_CHOICES,
        default='NO',
        verbose_name="Enfermedad mental familiar"
    )
    

    
   
    # 10. OTRO
    otros_antecedentes_familiares = models.TextField(
        blank=True, 
        verbose_name="Otros antecedentes familiares"
    )
    
    class Meta:
        verbose_name = "Antecedentes Familiares"
        verbose_name_plural = "Antecedentes Familiares"
        ordering = ['paciente__apellidos', 'paciente__nombres']
    
    def __str__(self):
        # ✅ CORREGIDO: Usa apellidos y nombres reales
        return f"Antecedentes familiares de {self.paciente.apellidos}, {self.paciente.nombres}"
    
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
        
        # ✅ AGREGADO: Otros antecedentes
        if self.otros_antecedentes_familiares.strip():
            antecedentes.append(f"Otros: {self.otros_antecedentes_familiares.strip()}")
        
        return antecedentes
