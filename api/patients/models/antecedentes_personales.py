# api/patients/models/anamnesis/antecedentes_personales.py

from django.db import models
from django.core.exceptions import ValidationError
from .base import BaseModel
from api.patients.models.paciente import Paciente

from .constants import (
    ALERGIA_ANTIBIOTICO_CHOICES,
    ALERGIA_ANESTESIA_CHOICES,
    HEMORRAGIAS_CHOICES,
    VIH_SIDA_CHOICES,
    TUBERCULOSIS_CHOICES,
    ASMA_CHOICES,
    DIABETES_CHOICES,
    HIPERTENSION_CHOICES,
    ENFERMEDAD_CARDIACA_CHOICES,
)


class AntecedentesPersonales(BaseModel):
    """
    Antecedentes patológicos personales del paciente (Sección D).
    """
    
    # Relación uno a uno con Paciente
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
    alergia_antibiotico_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Detalle alergia antibiótico",
        help_text="Amoxicilina, Cefalexina, etc."
    )
    
    # 2. ALERGIA ANESTESIA
    alergia_anestesia = models.CharField(
        max_length=20,
        choices=ALERGIA_ANESTESIA_CHOICES,
        default='NO',
        verbose_name="Alergia a anestesia"
    )
    alergia_anestesia_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Detalle alergia anestesia",
        help_text="Lidocaína, Bupivacaína, etc."
    )
    
    # 3. HEMORRAGIAS
    hemorragias = models.CharField(
        max_length=2,
        choices=HEMORRAGIAS_CHOICES,
        default='NO',
        verbose_name="Hemorragias"
    )
    hemorragias_detalle = models.TextField(
        blank=True,
        verbose_name="Detalle de hemorragias",
        help_text="Especificar tipo, frecuencia, tratamientos anticoagulantes, etc."
    )
    
    # 4. VIH / SIDA
    vih_sida = models.CharField(
        max_length=25,
        choices=VIH_SIDA_CHOICES,
        default='NEGATIVO',
        verbose_name="VIH/SIDA"
    )
    vih_sida_otro = models.CharField(  # ✅ NUEVO CAMPO
        max_length=100,
        blank=True,
        verbose_name="Detalle de condición inmunológica",
        help_text="Especificar otra condición inmunológica"
    )
    
    # 5. TUBERCULOSIS
    tuberculosis = models.CharField(
        max_length=25,
        choices=TUBERCULOSIS_CHOICES,
        default='NUNCA',
        verbose_name="Tuberculosis"
    )
    tuberculosis_otro = models.CharField(  # ✅ NUEVO CAMPO
        max_length=100,
        blank=True,
        verbose_name="Detalle de enfermedad pulmonar",
        help_text="Especificar otra enfermedad pulmonar"
    )
    
    # 6. ASMA
    asma = models.CharField(
        max_length=10,
        choices=ASMA_CHOICES,
        default='NO',
        verbose_name="Asma"
    )
    asma_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Detalle de asma",
        help_text="Especificar tipo o características particulares"
    )
    
    # 7. DIABETES
    diabetes = models.CharField(
        max_length=15,
        choices=DIABETES_CHOICES,
        default='NO',
        verbose_name="Diabetes"
    )
    diabetes_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Detalle diabetes",
        help_text="MODY, LADA, diabetes gestacional, etc."
    )
    
    # 8. HIPERTENSIÓN ARTERIAL
    hipertension_arterial = models.CharField(
        max_length=20,
        choices=HIPERTENSION_CHOICES,
        default='NO',
        verbose_name="Hipertensión arterial"
    )
    hipertension_arterial_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Detalle de hipertensión",
        help_text="Hipertensión secundaria, etc."
    )
    
    # 9. ENFERMEDAD CARDIACA
    enfermedad_cardiaca = models.CharField(
        max_length=20,
        choices=ENFERMEDAD_CARDIACA_CHOICES,
        default='NO',
        verbose_name="Enfermedad cardíaca"
    )
    enfermedad_cardiaca_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Detalle enfermedad cardíaca",
        help_text="Arritmia auricular, valvulopatía, etc."
    )
    
    # 10. OTROS ANTECEDENTES
    otros_antecedentes_personales = models.TextField(
        blank=True,
        verbose_name="Otros antecedentes personales",
        help_text="Otras enfermedades o condiciones no listadas anteriormente"
    )
    
    # HÁBITOS
    habitos = models.TextField(
        blank=True,
        verbose_name="Hábitos",
        help_text="Tabaco, alcohol, drogas, bruxismo, higiene bucal, etc."
    )
    
    # OBSERVACIONES
    observaciones = models.TextField(
        blank=True,
        verbose_name="Observaciones generales",
        help_text="Cualquier información adicional relevante"
    )
    
    class Meta:
        verbose_name = "Antecedente Personal"
        verbose_name_plural = "Antecedentes Personales"
        ordering = ['paciente__apellidos', 'paciente__nombres']
        indexes = [
            models.Index(fields=['paciente']),
            models.Index(fields=['alergia_antibiotico']),
            models.Index(fields=['alergia_anestesia']),
            models.Index(fields=['diabetes']),
            models.Index(fields=['hipertension_arterial']),
            models.Index(fields=['vih_sida']),
            models.Index(fields=['tuberculosis']),
        ]
    
    def __str__(self):
        return f"Antecedentes personales de {self.paciente.nombre_completo}"
    
    def clean(self):
        """Validaciones personalizadas"""
        errors = {}
        
        # Lista de todos los campos con sus correspondientes _otro
        campos_validar = [
            ('alergia_antibiotico', 'alergia_antibiotico_otro'),
            ('alergia_anestesia', 'alergia_anestesia_otro'),
            ('vih_sida', 'vih_sida_otro'),
            ('tuberculosis', 'tuberculosis_otro'),
            ('asma', 'asma_otro'),
            ('diabetes', 'diabetes_otro'),
            ('hipertension_arterial', 'hipertension_arterial_otro'),
            ('enfermedad_cardiaca', 'enfermedad_cardiaca_otro'),
        ]
        
        # Validar todos los campos con _otro
        for campo_principal, campo_otro in campos_validar:
            valor_principal = getattr(self, campo_principal)
            valor_otro = getattr(self, campo_otro, '')
            
            # Si es OTRO, el campo _otro es requerido
            if valor_principal == 'OTRO' and not valor_otro:
                errors[campo_otro] = f'Debe especificar detalles cuando selecciona "OTRO"'
            
            # Si NO es OTRO, el campo _otro debe estar vacío
            if valor_principal != 'OTRO' and valor_otro:
                errors[campo_otro] = f'No debe especificar detalles cuando no selecciona "OTRO"'
        
        # Validación especial para hemorragias
        if self.hemorragias == 'SI' and not self.hemorragias_detalle:
            errors['hemorragias_detalle'] = 'Debe especificar detalles de hemorragias'
        elif self.hemorragias == 'NO' and self.hemorragias_detalle:
            errors['hemorragias_detalle'] = 'No debe especificar detalles cuando no hay hemorragias'
        
        if errors:
            raise ValidationError(errors)
    
    @property
    def tiene_condiciones_importantes(self):
        """Verifica si tiene condiciones importantes para odontología"""
        return any([
            self.alergia_antibiotico != 'NO',
            self.alergia_anestesia != 'NO',
            self.hemorragias == 'SI',
            self.vih_sida != 'NEGATIVO',  # Actualizado para incluir OTRO
            self.tuberculosis not in ['NUNCA', 'DESCONOCIDO'],  # Actualizado para incluir OTRO
            self.diabetes != 'NO',
            self.hipertension_arterial != 'NO',
            self.enfermedad_cardiaca != 'NO',
        ])
    
    @property
    def lista_antecedentes(self):
        """Retorna lista de antecedentes personales activos"""
        antecedentes = []
        
        # Alergias
        if self.alergia_antibiotico != 'NO':
            texto = self.get_alergia_antibiotico_display()
            if self.alergia_antibiotico == 'OTRO' and self.alergia_antibiotico_otro:
                texto += f" ({self.alergia_antibiotico_otro})"
            antecedentes.append(f"Alergia antibiótico: {texto}")
        
        if self.alergia_anestesia != 'NO':
            texto = self.get_alergia_anestesia_display()
            if self.alergia_anestesia == 'OTRO' and self.alergia_anestesia_otro:
                texto += f" ({self.alergia_anestesia_otro})"
            antecedentes.append(f"Alergia anestesia: {texto}")
        
        # Hemorragias
        if self.hemorragias == 'SI':
            texto = "Hemorragias"
            if self.hemorragias_detalle:
                texto += f" ({self.hemorragias_detalle[:50]}...)" if len(self.hemorragias_detalle) > 50 else f" ({self.hemorragias_detalle})"
            antecedentes.append(texto)
        
        # VIH/SIDA
        if self.vih_sida != 'NEGATIVO':
            texto = f"VIH/SIDA: {self.get_vih_sida_display()}"
            if self.vih_sida == 'OTRO' and self.vih_sida_otro:
                texto += f" ({self.vih_sida_otro})"
            antecedentes.append(texto)
        
        # Tuberculosis
        if self.tuberculosis != 'NUNCA':
            texto = f"Tuberculosis: {self.get_tuberculosis_display()}"
            if self.tuberculosis == 'OTRO' and self.tuberculosis_otro:
                texto += f" ({self.tuberculosis_otro})"
            antecedentes.append(texto)
        
        # Asma
        if self.asma != 'NO':
            texto = f"Asma: {self.get_asma_display()}"
            if self.asma == 'OTRO' and self.asma_otro:
                texto += f" ({self.asma_otro})"
            antecedentes.append(texto)
        
        # Diabetes
        if self.diabetes != 'NO':
            texto = f"Diabetes: {self.get_diabetes_display()}"
            if self.diabetes_otro:
                texto += f" ({self.diabetes_otro})"
            antecedentes.append(texto)
        
        # Hipertensión
        if self.hipertension_arterial != 'NO':
            texto = f"Hipertensión: {self.get_hipertension_arterial_display()}"
            if self.hipertension_arterial == 'OTRO' and self.hipertension_arterial_otro:
                texto += f" ({self.hipertension_arterial_otro})"
            antecedentes.append(texto)
        
        # Enfermedad cardíaca
        if self.enfermedad_cardiaca != 'NO':
            texto = f"Enfermedad cardíaca: {self.get_enfermedad_cardiaca_display()}"
            if self.enfermedad_cardiaca == 'OTRO' and self.enfermedad_cardiaca_otro:
                texto += f" ({self.enfermedad_cardiaca_otro})"
            antecedentes.append(texto)
        
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
            self.vih_sida in ['POSITIVO', 'OTRO'] or
            self.tuberculosis in ['ACTIVA', 'OTRO'] or
            self.asma == 'SEVERA' or
            self.diabetes in ['TIPO_1', 'TIPO_2'] or
            self.hipertension_arterial in ['NO_CONTROLADA', 'SIN_TRATAMIENTO', 'OTRO'] or
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
            texto = self.get_alergia_antibiotico_display()
            if self.alergia_antibiotico == 'OTRO' and self.alergia_antibiotico_otro:
                texto += f" ({self.alergia_antibiotico_otro})"
            alergias.append(texto)
        if self.alergia_anestesia != 'NO':
            texto = self.get_alergia_anestesia_display()
            if self.alergia_anestesia == 'OTRO' and self.alergia_anestesia_otro:
                texto += f" ({self.alergia_anestesia_otro})"
            alergias.append(texto)
        return ', '.join(alergias) if alergias else 'Sin alergias'
    
    @property
    def resumen_condiciones(self):
        """Resumen de condiciones importantes para alertas"""
        condiciones = []
        
        if self.alergia_antibiotico != 'NO':
            condiciones.append("Alergia a antibióticos")
        if self.alergia_anestesia != 'NO':
            condiciones.append("Alergia a anestesia")
        if self.hemorragias == 'SI':
            condiciones.append("Hemorragias/Coagulación")
        if self.vih_sida != 'NEGATIVO':
            condiciones.append("Condición inmunológica")
        if self.tuberculosis not in ['NUNCA', 'DESCONOCIDO']:
            condiciones.append("Enfermedad pulmonar")
        if self.diabetes != 'NO':
            condiciones.append("Diabetes")
        if self.hipertension_arterial != 'NO':
            condiciones.append("Hipertensión")
        if self.enfermedad_cardiaca != 'NO':
            condiciones.append("Enfermedad cardíaca")
        
        return ", ".join(condiciones) if condiciones else "Sin condiciones de riesgo"
    
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
    
    @property
    def exigencias_quirurgicas(self):
        """Retorna las condiciones que requieren precauciones especiales en cirugía"""
        exigencias = []
        
        if self.alergia_anestesia != 'NO':
            exigencias.append("Precaución con anestesia")
        if self.hemorragias == 'SI':
            exigencias.append("Precaución con hemorragias")
        if self.diabetes != 'NO':
            exigencias.append("Control glucémico pre-operatorio")
        if self.hipertension_arterial != 'NO':
            exigencias.append("Control de presión arterial")
        if self.enfermedad_cardiaca != 'NO':
            exigencias.append("Evaluación cardiológica pre-operatoria")
        
        return exigencias
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)