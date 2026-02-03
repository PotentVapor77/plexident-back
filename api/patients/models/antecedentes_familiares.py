# api/patients/models/anamnesis/antecedentes_familiares.py

from django.db import models
from django.core.exceptions import ValidationError
from api.patients.models.base import BaseModel
from api.patients.models.paciente import Paciente
from .constants import (
    FAMILIAR_BASE_CHOICES,  # ✅ USAR ESTE EN LUGAR DE CHOICES INDIVIDUALES
    TIPO_CANCER_CHOICES,
)


class AntecedentesFamiliares(BaseModel):
    """
    Antecedentes patológicos familiares del paciente (Sección E).
    Todos los campos usan FAMILIAR_BASE_CHOICES
    """
    
    # ✅ Relación uno a uno con Paciente
    paciente = models.OneToOneField(
        Paciente,
        on_delete=models.CASCADE,
        related_name='antecedentes_familiares',
        verbose_name="Paciente"
    )
    
    # 1. CARDIOPATÍA
    cardiopatia_familiar = models.CharField(
        max_length=15,
        choices=FAMILIAR_BASE_CHOICES,
        default='NO',
        verbose_name="Cardiopatía familiar"
    )
    cardiopatia_familiar_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro familiar con cardiopatía"
    )
    
    # 2. HIPERTENSIÓN ARTERIAL
    hipertension_arterial_familiar = models.CharField(
        max_length=15,
        choices=FAMILIAR_BASE_CHOICES,
        default='NO',
        verbose_name="Hipertensión arterial familiar"
    )
    hipertension_arterial_familiar_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro familiar con hipertensión"
    )
    
    # 3. ENFERMEDAD C. VASCULAR
    enfermedad_vascular_familiar = models.CharField(
        max_length=15,
        choices=FAMILIAR_BASE_CHOICES,
        default='NO',
        verbose_name="Enfermedad vascular familiar"
    )
    enfermedad_vascular_familiar_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro familiar con enfermedad vascular"
    )
    
    # 4. ENDÓCRINO METABÓLICO
    endocrino_metabolico_familiar = models.CharField(
        max_length=15,
        choices=FAMILIAR_BASE_CHOICES,
        default='NO',
        verbose_name="Endócrino metabólico familiar"
    )
    endocrino_metabolico_familiar_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro familiar con endócrino metabólico"
    )
    
    # 5. CÁNCER
    cancer_familiar = models.CharField(
        max_length=15,
        choices=FAMILIAR_BASE_CHOICES,
        default='NO',
        verbose_name="Cáncer familiar"
    )
    cancer_familiar_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro familiar con cáncer"
    )
    tipo_cancer = models.CharField(
        max_length=20,
        choices=TIPO_CANCER_CHOICES,
        blank=True,
        verbose_name="Tipo de cáncer"
    )
    tipo_cancer_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro tipo de cáncer"
    )
    
    # 6. TUBERCULOSIS
    tuberculosis_familiar = models.CharField(
        max_length=15,
        choices=FAMILIAR_BASE_CHOICES,
        default='NO',
        verbose_name="Tuberculosis familiar"
    )
    tuberculosis_familiar_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro familiar con tuberculosis"
    )
    
    # 7. ENFERMEDAD MENTAL
    enfermedad_mental_familiar = models.CharField(
        max_length=15,
        choices=FAMILIAR_BASE_CHOICES,
        default='NO',
        verbose_name="Enfermedad mental familiar"
    )
    enfermedad_mental_familiar_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro familiar con enfermedad mental"
    )
    
    # 8. ENFERMEDAD INFECCIOSA
    enfermedad_infecciosa_familiar = models.CharField(
        max_length=15,
        choices=FAMILIAR_BASE_CHOICES,
        default='NO',
        verbose_name="Enfermedad infecciosa familiar"
    )
    enfermedad_infecciosa_familiar_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro familiar con enfermedad infecciosa"
    )
    
    # 9. MALFORMACIÓN
    malformacion_familiar = models.CharField(
        max_length=15,
        choices=FAMILIAR_BASE_CHOICES,
        default='NO',
        verbose_name="Malformación familiar"
    )
    malformacion_familiar_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro familiar con malformación"
    )
    
    # 10. OTROS
    otros_antecedentes_familiares = models.TextField(
        blank=True,
        verbose_name="Otros antecedentes familiares"
    )
    
    class Meta:
        verbose_name = "Antecedentes Familiares"
        verbose_name_plural = "Antecedentes Familiares"
        ordering = ['paciente__apellidos', 'paciente__nombres']
        indexes = [
            models.Index(fields=['paciente']),
        ]
    
    def __str__(self):
        return f"Antecedentes familiares de {self.paciente.apellidos}, {self.paciente.nombres}"
    
    def clean(self):
        """Validaciones personalizadas"""
        errors = {}
        
        # Validar campos "OTRO"
        if self.cardiopatia_familiar == 'OTRO' and not self.cardiopatia_familiar_otro:
            errors['cardiopatia_familiar_otro'] = 'Debe especificar el familiar cuando selecciona "Otro"'
        
        if self.hipertension_arterial_familiar == 'OTRO' and not self.hipertension_arterial_familiar_otro:
            errors['hipertension_arterial_familiar_otro'] = 'Debe especificar el familiar cuando selecciona "Otro"'
        
        if self.enfermedad_vascular_familiar == 'OTRO' and not self.enfermedad_vascular_familiar_otro:
            errors['enfermedad_vascular_familiar_otro'] = 'Debe especificar el familiar cuando selecciona "Otro"'
        
        if self.endocrino_metabolico_familiar == 'OTRO' and not self.endocrino_metabolico_familiar_otro:
            errors['endocrino_metabolico_familiar_otro'] = 'Debe especificar el familiar cuando selecciona "Otro"'
        
        if self.cancer_familiar == 'OTRO' and not self.cancer_familiar_otro:
            errors['cancer_familiar_otro'] = 'Debe especificar el familiar cuando selecciona "Otro"'
        
        if self.tuberculosis_familiar == 'OTRO' and not self.tuberculosis_familiar_otro:
            errors['tuberculosis_familiar_otro'] = 'Debe especificar el familiar cuando selecciona "Otro"'
        
        if self.enfermedad_mental_familiar == 'OTRO' and not self.enfermedad_mental_familiar_otro:
            errors['enfermedad_mental_familiar_otro'] = 'Debe especificar el familiar cuando selecciona "Otro"'
        
        if self.enfermedad_infecciosa_familiar == 'OTRO' and not self.enfermedad_infecciosa_familiar_otro:
            errors['enfermedad_infecciosa_familiar_otro'] = 'Debe especificar el familiar cuando selecciona "Otro"'
        
        if self.malformacion_familiar == 'OTRO' and not self.malformacion_familiar_otro:
            errors['malformacion_familiar_otro'] = 'Debe especificar el familiar cuando selecciona "Otro"'
        
        # Validar tipo de cáncer
        if self.cancer_familiar != 'NO' and not self.tipo_cancer:
            errors['tipo_cancer'] = 'Debe especificar el tipo de cáncer'
        
        if self.tipo_cancer == 'OTRO' and not self.tipo_cancer_otro:
            errors['tipo_cancer_otro'] = 'Debe especificar el tipo de cáncer cuando selecciona "Otro"'
        
        if errors:
            raise ValidationError(errors)
    
    @property
    def tiene_antecedentes_importantes(self):
        """Verifica si tiene antecedentes familiares importantes"""
        return any([
            self.cardiopatia_familiar != 'NO',
            self.hipertension_arterial_familiar != 'NO',
            self.enfermedad_vascular_familiar != 'NO',
            self.endocrino_metabolico_familiar != 'NO',
            self.cancer_familiar != 'NO',
            self.tuberculosis_familiar != 'NO',
            self.enfermedad_mental_familiar != 'NO',
            self.enfermedad_infecciosa_familiar != 'NO',
            self.malformacion_familiar != 'NO',
        ])
    
    @property
    def lista_antecedentes(self):
        """Retorna lista de antecedentes familiares activos"""
        antecedentes = []
        
        if self.cardiopatia_familiar != 'NO':
            texto = f"Cardiopatía: {self.get_cardiopatia_familiar_display()}"
            if self.cardiopatia_familiar == 'OTRO' and self.cardiopatia_familiar_otro:
                texto += f" ({self.cardiopatia_familiar_otro})"
            antecedentes.append(texto)
        
        if self.hipertension_arterial_familiar != 'NO':
            texto = f"Hipertensión: {self.get_hipertension_arterial_familiar_display()}"
            if self.hipertension_arterial_familiar == 'OTRO' and self.hipertension_arterial_familiar_otro:
                texto += f" ({self.hipertension_arterial_familiar_otro})"
            antecedentes.append(texto)
        
        if self.enfermedad_vascular_familiar != 'NO':
            texto = f"Enf. vascular: {self.get_enfermedad_vascular_familiar_display()}"
            if self.enfermedad_vascular_familiar == 'OTRO' and self.enfermedad_vascular_familiar_otro:
                texto += f" ({self.enfermedad_vascular_familiar_otro})"
            antecedentes.append(texto)
        
        if self.endocrino_metabolico_familiar != 'NO':
            texto = f"Endócrino metabólico: {self.get_endocrino_metabolico_familiar_display()}"
            if self.endocrino_metabolico_familiar == 'OTRO' and self.endocrino_metabolico_familiar_otro:
                texto += f" ({self.endocrino_metabolico_familiar_otro})"
            antecedentes.append(texto)
        
        if self.cancer_familiar != 'NO':
            texto = f"Cáncer: {self.get_cancer_familiar_display()}"
            if self.cancer_familiar == 'OTRO' and self.cancer_familiar_otro:
                texto += f" ({self.cancer_familiar_otro})"
            if self.tipo_cancer:
                tipo_texto = self.get_tipo_cancer_display()
                if self.tipo_cancer == 'OTRO' and self.tipo_cancer_otro:
                    tipo_texto = self.tipo_cancer_otro
                texto += f" - Tipo: {tipo_texto}"
            antecedentes.append(texto)
        
        if self.tuberculosis_familiar != 'NO':
            texto = f"Tuberculosis: {self.get_tuberculosis_familiar_display()}"
            if self.tuberculosis_familiar == 'OTRO' and self.tuberculosis_familiar_otro:
                texto += f" ({self.tuberculosis_familiar_otro})"
            antecedentes.append(texto)
        
        if self.enfermedad_mental_familiar != 'NO':
            texto = f"Enf. mental: {self.get_enfermedad_mental_familiar_display()}"
            if self.enfermedad_mental_familiar == 'OTRO' and self.enfermedad_mental_familiar_otro:
                texto += f" ({self.enfermedad_mental_familiar_otro})"
            antecedentes.append(texto)
        
        if self.enfermedad_infecciosa_familiar != 'NO':
            texto = f"Enfermedad infecciosa: {self.get_enfermedad_infecciosa_familiar_display()}"
            if self.enfermedad_infecciosa_familiar == 'OTRO' and self.enfermedad_infecciosa_familiar_otro:
                texto += f" ({self.enfermedad_infecciosa_familiar_otro})"
            antecedentes.append(texto)
        
        if self.malformacion_familiar != 'NO':
            texto = f"Malformación: {self.get_malformacion_familiar_display()}"
            if self.malformacion_familiar == 'OTRO' and self.malformacion_familiar_otro:
                texto += f" ({self.malformacion_familiar_otro})"
            antecedentes.append(texto)
        
        if self.otros_antecedentes_familiares.strip():
            antecedentes.append(f"Otros: {self.otros_antecedentes_familiares.strip()}")
        
        return antecedentes
    
    @property
    def resumen_antecedentes(self):
        """Resumen de antecedentes familiares importantes"""
        antecedentes = []
        
        if self.cardiopatia_familiar != 'NO':
            antecedentes.append(f"Cardiopatía ({self.get_cardiopatia_familiar_display()})")
        if self.hipertension_arterial_familiar != 'NO':
            antecedentes.append(f"Hipertensión ({self.get_hipertension_arterial_familiar_display()})")
        if self.cancer_familiar != 'NO':
            texto = f"Cáncer ({self.get_cancer_familiar_display()})"
            if self.tipo_cancer:
                texto += f" - {self.get_tipo_cancer_display()}"
            antecedentes.append(texto)
        if self.endocrino_metabolico_familiar != 'NO':
            antecedentes.append(f"Endocrino-metabólico ({self.get_endocrino_metabolico_familiar_display()})")
        
        return ", ".join(antecedentes) if antecedentes else "Sin antecedentes familiares relevantes"
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
