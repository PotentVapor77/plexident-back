# patients/models/anamnesis_general.py

from django.db import models
from django.core.exceptions import ValidationError
from .base import BaseModel
from .paciente import Paciente

# ================== CONSTANTES ==================

# Sección D: ANTECEDENTES PATOLÓGICOS PERSONALES - Opciones

# 1. ALERGIA A ANTIBIÓTICOS - Top 5 + Otro
ALERGIA_ANTIBIOTICO_CHOICES = [
    ('NO', 'No'),
    ('PENICILINA', 'Penicilina'),
    ('AMOXICILINA', 'Amoxicilina'),
    ('CEFALEXINA', 'Cefalexina'),
    ('AZITROMICINA', 'Azitromicina'),
    ('CLARITROMICINA', 'Claritromicina'),
    ('OTRO', 'Otro'),
]

# 2. ALERGIA A ANESTESIA - Top 5 + Otro
ALERGIA_ANESTESIA_CHOICES = [
    ('NO', 'No'),
    ('LIDOCAINA', 'Lidocaína'),
    ('ARTICAINA', 'Articaina'),
    ('MEPIVACAINA', 'Mepivacaina'),
    ('BUPIVACAINA', 'Bupivacaina'),
    ('PRILOCAINA', 'Prilocaina'),
    ('OTRO', 'Otro'),
]

# 3. HEMORRAGIAS - Simple: Sí o No
HEMORRAGIAS_CHOICES = [
    ('NO', 'No'),
    ('SI', 'Sí'),
]

# 4. VIH / SIDA - Top 5 + Otro
VIH_SIDA_CHOICES = [
    ('NEGATIVO', 'Negativo'),
    ('POSITIVO_TRATADO', 'Positivo - En tratamiento'),
    ('POSITIVO_NO_TRATADO', 'Positivo - Sin tratamiento'),
    ('NO_SABE', 'No sabe / No realizado'),
    ('RESTRICCION', 'Prefiere no decir'),
    ('INDETERMINADO', 'Resultado indeterminado'),
    ('OTRO', 'Otro'),
]

# 5. TUBERCULOSIS - Top 5 + Otro
TUBERCULOSIS_CHOICES = [
    ('NO', 'No'),
    ('TRATADA_CURADA', 'Tratada y curada'),
    ('ACTIVA_TRATAMIENTO', 'Activa - En tratamiento'),
    ('ACTIVA_NO_TRATAMIENTO', 'Activa - Sin tratamiento'),
    ('CONTACTO', 'Contacto con enfermo'),
    ('VACUNA_BCG', 'Solo vacuna BCG'),
    ('OTRO', 'Otro'),
]

# 6. ASMA - Top 5 + Otro
ASMA_CHOICES = [
    ('NO', 'No'),
    ('LEVE_INTERMITENTE', 'Leve Intermitente'),
    ('LEVE_PERSISTENTE', 'Leve Persistente'),
    ('MODERADA_PERSISTENTE', 'Moderada Persistente'),
    ('GRAVE_PERSISTENTE', 'Grave Persistente'),
    ('INDUCIDA_EJERCICIO', 'Inducida por ejercicio'),
    ('OTRO', 'Otro'),
]

# 7. DIABETES - Top 5 + Otro
DIABETES_CHOICES = [
    ('NO', 'No'),
    ('TIPO_1', 'Tipo 1 (Insulinodependiente)'),
    ('TIPO_2', 'Tipo 2'),
    ('GESTACIONAL', 'Gestacional'),
    ('PREDIABETES', 'Prediabetes'),
    ('LADA', 'LADA (Diabetes autoinmune latente)'),
    ('OTRO', 'Otro'),
]

# 8. HIPERTENSIÓN - Top 5 + Otro
HIPERTENSION_CHOICES = [
    ('NO', 'No'),
    ('CONTROLADA', 'Controlada con medicación'),
    ('LIMITROFE', 'Límite/Borderline'),
    ('NO_CONTROLADA', 'No controlada'),
    ('RESISTENTE', 'Hipertensión resistente'),
    ('MALIGNA', 'Hipertensión maligna'),
    ('OTRO', 'Otro'),
]

# 9. ENFERMEDAD CARDÍACA - Top 5 + Otro
ENFERMEDAD_CARDIACA_CHOICES = [
    ('NO', 'No'),
    ('HIPERTENSION', 'Hipertensión arterial'),
    ('INSUFICIENCIA_CARDIACA', 'Insuficiencia cardíaca'),
    ('ARRITMIA', 'Arritmias'),
    ('CARDIOPATIA_ISQUEMICA', 'Cardiopatía isquémica'),
    ('VALVULOPATIA', 'Valvulopatía'),
    ('OTRA', 'Otra'),
]

# 10. ANTECEDENTES FAMILIARES - Top 5 + Ninguno
FAMILIAR_BASE_CHOICES = [
    ('NO', 'Ninguno'),
    ('PADRE', 'Padre'),
    ('MADRE', 'Madre'),
    ('ABUELOS', 'Abuelos'),
    ('HERMANOS', 'Hermanos'),
    ('TIO', 'Tíos'),
    ('OTRO', 'Otro familiar'),
]

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
    
    # ================== SECCIÓN D: ANTECEDENTES PATOLÓGICOS PERSONALES ==================
    
    # 1. ALERGIAS A ANTIBIÓTICOS - Top 5 + Otro
    alergia_antibiotico = models.CharField(
        max_length=20,
        choices=ALERGIA_ANTIBIOTICO_CHOICES,
        default='NO',
        verbose_name="Alergia a antibióticos"
    )
    alergia_antibiotico_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro antibiótico",
        help_text="Si seleccionó 'Otro', especificar cuál"
    )
    
    
    # 2. ALERGIAS A ANESTESIA - Top 5 + Otro
    alergia_anestesia = models.CharField(
        max_length=20,
        choices=ALERGIA_ANESTESIA_CHOICES,
        default='NO',
        verbose_name="Alergia a anestesia"
    )
    alergia_anestesia_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro tipo de anestesia",
        help_text="Si seleccionó 'Otro', especificar cuál"
    )
    
  
    # 4. HEMORRAGIAS / PROBLEMAS DE COAGULACIÓN
    problemas_coagulacion = models.CharField(
        max_length=2,
        choices=HEMORRAGIAS_CHOICES,
        default='NO',
        verbose_name="¿Problemas de coagulación?"
    )
    
    # 5. VIH / SIDA - Top 5 + Otro
    vih_sida = models.CharField(
        max_length=25,
        choices=VIH_SIDA_CHOICES,
        default='NEGATIVO',
        verbose_name="VIH/SIDA"
    )
    vih_sida_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro estado VIH/SIDA",
        help_text="Si seleccionó 'Otro', especificar cuál"
    )
    
    # 6. TUBERCULOSIS - Top 5 + Otro
    tuberculosis = models.CharField(
        max_length=25,
        choices=TUBERCULOSIS_CHOICES,
        default='NO',
        verbose_name="Tuberculosis"
    )
    tuberculosis_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro estado tuberculosis",
        help_text="Si seleccionó 'Otro', especificar cuál"
    )
    
    # 7. ASMA - Top 5 + Otro
    asma = models.CharField(
        max_length=25,
        choices=ASMA_CHOICES,
        default='NO',
        verbose_name="Asma"
    )
    asma_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro tipo de asma",
        help_text="Si seleccionó 'Otro', especificar cuál"
    )
    
    # 8. DIABETES - Top 5 + Otro
    diabetes = models.CharField(
        max_length=20,
        choices=DIABETES_CHOICES,
        default='NO',
        verbose_name="Diabetes"
    )
    diabetes_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro tipo de diabetes",
        help_text="Si seleccionó 'Otro', especificar cuál"
    )
    
    # 9. HIPERTENSIÓN - Top 5 + Otro
    hipertension = models.CharField(
        max_length=20,
        choices=HIPERTENSION_CHOICES,
        default='NO',
        verbose_name="Hipertensión"
    )
    hipertension_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro tipo de hipertensión",
        help_text="Si seleccionó 'Otro', especificar cuál"
    )
    
    # 10. ENFERMEDAD CARDÍACA - Top 5 + Otro
    enfermedad_cardiaca = models.CharField(
        max_length=25,
        choices=ENFERMEDAD_CARDIACA_CHOICES,
        default='NO',
        verbose_name="Enfermedad cardíaca"
    )
    enfermedad_cardiaca_otra = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otra enfermedad cardíaca",
        help_text="Si seleccionó 'Otra', especificar cuál"
    )
    

    
    # ================== SECCIÓN E: ANTECEDENTES PATOLÓGICOS FAMILIARES ==================
    
    # 1. CARDIOPATÍA FAMILIAR - Top 5 + Ninguno
    cardiopatia_familiar = models.CharField(
        max_length=20,
        choices=FAMILIAR_BASE_CHOICES,
        default='NO',
        verbose_name="Cardiopatía en familiares"
    )
    cardiopatia_familiar_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro familiar",
        help_text="Si seleccionó 'Otro familiar', especificar cuál"
    )
    
    # 2. HIPERTENSIÓN FAMILIAR - Top 5 + Ninguno
    hipertension_familiar = models.CharField(
        max_length=20,
        choices=FAMILIAR_BASE_CHOICES,
        default='NO',
        verbose_name="Hipertensión en familiares"
    )
    hipertension_familiar_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro familiar",
        help_text="Si seleccionó 'Otro familiar', especificar cuál"
    )
    
    # 3. DIABETES FAMILIAR - Top 5 + Ninguno
    diabetes_familiar = models.CharField(
        max_length=20,
        choices=FAMILIAR_BASE_CHOICES,
        default='NO',
        verbose_name="Diabetes en familiares"
    )
    diabetes_familiar_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro familiar",
        help_text="Si seleccionó 'Otro familiar', especificar cuál"
    )
    
    # 4. CÁNCER FAMILIAR - Top 5 + Ninguno
    cancer_familiar = models.CharField(
        max_length=20,
        choices=FAMILIAR_BASE_CHOICES,
        default='NO',
        verbose_name="Cáncer en familiares"
    )
    cancer_familiar_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro familiar",
        help_text="Si seleccionó 'Otro familiar', especificar cuál"
    )
    
    # 5. ENFERMEDADES MENTALES FAMILIARES - Top 5 + Ninguno
    enfermedad_mental_familiar = models.CharField(
        max_length=20,
        choices=FAMILIAR_BASE_CHOICES,
        default='NO',
        verbose_name="Enfermedades mentales en familiares"
    )
    enfermedad_mental_familiar_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro familiar",
        help_text="Si seleccionó 'Otro familiar', especificar cuál"
    )
    
    # ================== HÁBITOS ==================
    habitos = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Hábitos",
        help_text="Tabaco, alcohol, drogas, bruxismo, etc."
    )
    
    # ================== OBSERVACIONES GENERALES ==================
    observaciones = models.TextField(
        blank=True,
        verbose_name="Observaciones generales",
        help_text="Cualquier información adicional relevante"
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
        errors = {}
        
        # Validar campos "Otro" que requieren especificación
        campos_otro = [
            ('alergia_antibiotico', 'alergia_antibiotico_otro', 'OTRO'),
            ('alergia_anestesia', 'alergia_anestesia_otro', 'OTRO'),
            ('vih_sida', 'vih_sida_otro', 'OTRO'),
            ('tuberculosis', 'tuberculosis_otro', 'OTRO'),
            ('asma', 'asma_otro', 'OTRO'),
            ('diabetes', 'diabetes_otro', 'OTRO'),
            ('hipertension', 'hipertension_otro', 'OTRO'),
            ('enfermedad_cardiaca', 'enfermedad_cardiaca_otra', 'OTRA'),
            ('cardiopatia_familiar', 'cardiopatia_familiar_otro', 'OTRO'),
            ('hipertension_familiar', 'hipertension_familiar_otro', 'OTRO'),
            ('diabetes_familiar', 'diabetes_familiar_otro', 'OTRO'),
            ('cancer_familiar', 'cancer_familiar_otro', 'OTRO'),
            ('enfermedad_mental_familiar', 'enfermedad_mental_familiar_otro', 'OTRO'),
        ]
        
        for campo_select, campo_otro, valor_otro in campos_otro:
            valor_select = getattr(self, campo_select)
            valor_otro_field = getattr(self, campo_otro)
            
            if valor_select == valor_otro and not valor_otro_field:
                nombre_display = getattr(self, f'get_{campo_select}_display')()
                errors[campo_otro] = f'Debe especificar cuando selecciona "{nombre_display}"'
        
        if errors:
            raise ValidationError(errors)
    
    # Métodos helper para obtener texto completo
    def get_display_completo(self, campo_select, campo_otro, valor_otro='OTRO'):
        """Obtiene el texto completo para campos con opción 'Otro'"""
        valor = getattr(self, campo_select)
        if valor == valor_otro:
            otro_texto = getattr(self, campo_otro, '')
            return f"Otro: {otro_texto}" if otro_texto else "Otro (no especificado)"
        return self._get_choice_display(campo_select, valor)
    
    def _get_choice_display(self, field_name, value):
        """Helper para obtener display de choices"""
        field = self._meta.get_field(field_name)
        return dict(field.choices).get(value, value)
    
    # Métodos específicos para cada campo
    def get_alergia_antibiotico_display_completo(self):
        return self.get_display_completo('alergia_antibiotico', 'alergia_antibiotico_otro')
    
    def get_alergia_anestesia_display_completo(self):
        return self.get_display_completo('alergia_anestesia', 'alergia_anestesia_otro')
    
    def get_vih_sida_display_completo(self):
        return self.get_display_completo('vih_sida', 'vih_sida_otro')
    
    def get_tuberculosis_display_completo(self):
        return self.get_display_completo('tuberculosis', 'tuberculosis_otro')
    
    def get_asma_display_completo(self):
        return self.get_display_completo('asma', 'asma_otro')
    
    def get_diabetes_display_completo(self):
        return self.get_display_completo('diabetes', 'diabetes_otro')
    
    def get_hipertension_display_completo(self):
        return self.get_display_completo('hipertension', 'hipertension_otro')
    
    def get_enfermedad_cardiaca_display_completo(self):
        return self.get_display_completo('enfermedad_cardiaca', 'enfermedad_cardiaca_otra', 'OTRA')
    
    @property
    def resumen_condiciones(self):
        """Resumen de condiciones importantes"""
        condiciones = []
        
        if self.alergia_antibiotico != 'NO':
            condiciones.append(f"Alergia antibióticos: {self.get_alergia_antibiotico_display_completo()}")
        
        if self.alergia_anestesia != 'NO':
            condiciones.append(f"Alergia anestesia: {self.get_alergia_anestesia_display_completo()}")
        
        if self.problemas_coagulacion == 'SI':
            condiciones.append("Problemas coagulación")
        
        if self.vih_sida not in ['NEGATIVO', 'NO_SABE']:
            condiciones.append(f"VIH/SIDA: {self.get_vih_sida_display_completo()}")
        
        if self.tuberculosis not in ['NO', 'VACUNA_BCG']:
            condiciones.append(f"Tuberculosis: {self.get_tuberculosis_display_completo()}")
        
        if self.diabetes != 'NO':
            condiciones.append(f"Diabetes: {self.get_diabetes_display_completo()}")
        
        if self.hipertension != 'NO':
            condiciones.append(f"Hipertensión: {self.get_hipertension_display_completo()}")
        
        if self.enfermedad_cardiaca != 'NO':
            condiciones.append(f"Enfermedad cardíaca: {self.get_enfermedad_cardiaca_display_completo()}")
        
        
        return "; ".join(condiciones) if condiciones else "Sin condiciones de riesgo"
    
    def save(self, *args, **kwargs):
        """Método save con validaciones automáticas"""
        self.full_clean()
        super().save(*args, **kwargs)