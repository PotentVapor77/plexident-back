# patients/models/anamnesis_general.py

from django.db import models
from django.core.exceptions import ValidationError
from .base import BaseModel
from .paciente import Paciente

class AnamnesisGeneral(BaseModel):
    """
    Anamnesis general del paciente según ficha clínica odontológica.
    Incluye información clínica complementaria a los datos personales.
    """
    
    # ✅ Relación uno a uno con Paciente
    paciente = models.OneToOneField(
        Paciente,
        on_delete=models.CASCADE,
        related_name='anamnesis_general',
        verbose_name="Paciente"
    )
    
    # ================== ALERGIAS ==================
    tiene_alergias = models.BooleanField(
        default=False,
        verbose_name="¿Tiene alergias?"
    )

    alergias_detalle = models.TextField(
        blank=True,
        verbose_name="Detalle de alergias",
        help_text="Especificar tipo de alergias (medicamentos, alimentos, materiales dentales, etc.)"
    )
    
    # ================== ANTECEDENTES PERSONALES ==================
    antecedentes_personales = models.TextField(
        blank=True,
        verbose_name="Antecedentes personales",
        help_text="Enfermedades previas, cirugías, hospitalizaciones, etc."
    )
    
    # ================== ANTECEDENTES FAMILIARES ==================
    antecedentes_familiares = models.TextField(
        blank=True,
        verbose_name="Antecedentes familiares",
        help_text="Enfermedades hereditarias, diabetes, hipertensión, cáncer, etc."
    )
    
    # ================== PROBLEMAS DE COAGULACIÓN ==================
    problemas_coagulacion = models.BooleanField(
        default=False,
        verbose_name="¿Problemas de coagulación?"
    )
    problemas_coagulacion_detalle = models.TextField(
        blank=True,
        verbose_name="Detalle de problemas de coagulación",
        help_text="Especificar tipo de problema, medicación anticoagulante, etc."
    )
    
    # ================== PROBLEMAS CON ANESTÉSICOS LOCALES ==================
    problemas_anestesicos = models.BooleanField(
        default=False,
        verbose_name="¿Problemas con anestésicos locales?"
    )
    problemas_anestesicos_detalle = models.TextField(
        blank=True,
        verbose_name="Detalle de problemas con anestésicos",
        help_text="Especificar reacciones adversas previas"
    )
    
    # ================== ADMINISTRACIÓN ACTUAL DE MEDICAMENTOS ==================
    toma_medicamentos = models.BooleanField(
        default=False,
        verbose_name="¿Toma medicamentos actualmente?"
    )
    medicamentos_actuales = models.TextField(
        blank=True,
        verbose_name="Medicamentos actuales (detallado)",
        help_text="Nombre, dosis, frecuencia, motivo"
    )
    
    # ================== HÁBITOS ==================
    habitos = models.TextField(
        blank=True,
        verbose_name="Hábitos",
        help_text="Tabaco, alcohol, drogas, bruxismo, morderse las uñas, etc."
    )
    
    # ================== OTROS ==================
    otros = models.TextField(
        blank=True,
        verbose_name="Otros",
        help_text="Cualquier otra información relevante no contemplada anteriormente"
    )
    
    class Meta:
        verbose_name = "Anamnesis General"
        verbose_name_plural = "Anamnesis Generales"
        ordering = ['-fecha_modificacion']
        indexes = [
            models.Index(fields=['paciente']),
        ]
    
    def __str__(self):
        return f"Anamnesis de {self.paciente.nombre_completo}"
    
    def clean(self):
        """Validaciones personalizadas"""
        # Si tiene alergias, debe especificar
        if self.tiene_alergias and not self.alergias_detalle:
            raise ValidationError({
                'alergias_detalle': 'Debe especificar las alergias del paciente'
            })
        
        # Si tiene problemas de coagulación, debe detallar
        if self.problemas_coagulacion and not self.problemas_coagulacion_detalle:
            raise ValidationError({
                'problemas_coagulacion_detalle': 'Debe especificar los problemas de coagulación'
            })
        
        # Si tiene problemas con anestésicos, debe detallar
        if self.problemas_anestesicos and not self.problemas_anestesicos_detalle:
            raise ValidationError({
                'problemas_anestesicos_detalle': 'Debe especificar los problemas con anestésicos'
            })
        
        # Si toma medicamentos, debe especificar cuáles
        if self.toma_medicamentos and not self.medicamentos_actuales:
            raise ValidationError({
                'medicamentos_actuales': 'Debe especificar los medicamentos que toma actualmente'
            })
    
    def save(self, *args, **kwargs):
        """Método save con validaciones automáticas"""
        self.full_clean()
        super().save(*args, **kwargs)
