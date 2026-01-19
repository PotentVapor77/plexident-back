# patients/models/anamnesis_general.py

from django.db import models
from django.core.exceptions import ValidationError
from .base import BaseModel
from .paciente import Paciente

# ================== CONSTANTES ==================

# ALERGIA ANTIBIÓTICO
ALERGIA_ANTIBIOTICO_CHOICES = [
    ('NO', 'No'),
    ('PENICILINA', 'Penicilina'),
    ('AMOXICILINA', 'Amoxicilina'),
    ('CEFALEXINA', 'Cefalexina'),
    ('AZITROMICINA', 'Azitromicina'),
    ('CLARITROMICINA', 'Claritromicina'),
    ('OTRO', 'Otro'),
]

# ALERGIA ANESTESIA
ALERGIA_ANESTESIA_CHOICES = [
    ('NO', 'No'),
    ('LIDOCAINA', 'Lidocaína'),
    ('ARTICAINA', 'Articaina'),
    ('MEPIVACAINA', 'Mepivacaina'),
    ('BUPIVACAINA', 'Bupivacaina'),
    ('PRILOCAINA', 'Prilocaina'),
    ('OTRO', 'Otro'),
]

# HEMORRAGIAS
HEMORRAGIAS_CHOICES = [
    ('NO', 'No'),
    ('SI', 'Sí'),
]

# VIH / SIDA
VIH_SIDA_CHOICES = [
    ('NEGATIVO', 'Negativo'),
    ('POSITIVO_TRATADO', 'Positivo - En tratamiento'),
    ('POSITIVO_NO_TRATADO', 'Positivo - Sin tratamiento'),
    ('NO_SABE', 'No sabe / No realizado'),
    ('RESTRICCION', 'Prefiere no decir'),
    ('INDETERMINADO', 'Resultado indeterminado'),
    ('OTRO', 'Otro'),
]

# TUBERCULOSIS
TUBERCULOSIS_CHOICES = [
    ('NO', 'No'),
    ('TRATADA_CURADA', 'Tratada y curada'),
    ('ACTIVA_TRATAMIENTO', 'Activa - En tratamiento'),
    ('ACTIVA_NO_TRATAMIENTO', 'Activa - Sin tratamiento'),
    ('CONTACTO', 'Contacto con enfermo'),
    ('VACUNA_BCG', 'Solo vacuna BCG'),
    ('OTRO', 'Otro'),
]

# ASMA
ASMA_CHOICES = [
    ('NO', 'No'),
    ('LEVE_INTERMITENTE', 'Leve Intermitente'),
    ('LEVE_PERSISTENTE', 'Leve Persistente'),
    ('MODERADA_PERSISTENTE', 'Moderada Persistente'),
    ('GRAVE_PERSISTENTE', 'Grave Persistente'),
    ('INDUCIDA_EJERCICIO', 'Inducida por ejercicio'),
    ('OTRO', 'Otro'),
]

# DIABETES
DIABETES_CHOICES = [
    ('NO', 'No'),
    ('TIPO_1', 'Tipo 1 (Insulinodependiente)'),
    ('TIPO_2', 'Tipo 2'),
    ('GESTACIONAL', 'Gestacional'),
    ('PREDIABETES', 'Prediabetes'),
    ('LADA', 'LADA (Diabetes autoinmune latente)'),
    ('OTRO', 'Otro'),
]

# HIPERTENSIÓN ARTERIAL
HIPERTENSION_ARTERIAL_CHOICES = [
    ('NO', 'No'),
    ('CONTROLADA', 'Controlada con medicación'),
    ('LIMITROFE', 'Límite/Borderline'),
    ('NO_CONTROLADA', 'No controlada'),
    ('RESISTENTE', 'Hipertensión resistente'),
    ('MALIGNA', 'Hipertensión maligna'),
    ('OTRO', 'Otro'),
]

# ENFERMEDAD CARDIACA
ENF_CARDIACA_CHOICES = [
    ('NO', 'No'),
    ('CARDIOPATIA_ISQUEMICA', 'Cardiopatía isquémica'),
    ('INSUFICIENCIA_CARDIACA', 'Insuficiencia cardíaca'),
    ('ARRITMIA', 'Arritmias'),
    ('VALVULOPATIA', 'Valvulopatía'),
    ('CARDIOMIOPATIA', 'Cardiomiopatía'),
    ('OTRO', 'Otro'),
]

# ENFERMEDADES GENERALES
ENFERMEDAD_GENERAL_CHOICES = [
    ('NO', 'No'),
    ('SI', 'Sí'),
]

# ANTECEDENTES FAMILIARES BASE
FAMILIAR_BASE_CHOICES = [
    ('NO', 'Ninguno'),
    ('PADRE', 'Padre'),
    ('MADRE', 'Madre'),
    ('ABUELOS', 'Abuelos'),
    ('HERMANOS', 'Hermanos'),
    ('TIO', 'Tíos'),
    ('OTRO', 'Otro'),
]

# ENFERMEDAD CEREBROVASCULAR
ENF_CEREBROVASCULAR_CHOICES = [
    ('NO', 'No'),
    ('ACCIDENTE_CEREBROVASCULAR', 'Accidente cerebrovascular'),
    ('ICTUS', 'Ictus'),
    ('ANEURISMA', 'Aneurisma cerebral'),
    ('DEMENCIA_VASCULAR', 'Demencia vascular'),
    ('OTRO', 'Otro'),
]

# ENDÓCRINO METABÓLICO
ENDOCRINO_METABOLICO_CHOICES = [
    ('NO', 'No'),
    ('TIROIDES', 'Enfermedad tiroidea'),
    ('OBESIDAD', 'Obesidad'),
    ('DISLIPIDEMIA', 'Dislipidemia'),
    ('SINDROME_METABOLICO', 'Síndrome metabólico'),
    ('OTRO', 'Otro'),
]

# CÁNCER
CANCER_CHOICES = [
    ('NO', 'No'),
    ('PULMON', 'Cáncer de pulmón'),
    ('MAMA', 'Cáncer de mama'),
    ('COLON', 'Cáncer de colon'),
    ('PROSTATA', 'Cáncer de próstata'),
    ('LEUCEMIA', 'Leucemia'),
    ('OTRO', 'Otro'),
]

# ENFERMEDAD MENTAL
ENF_MENTAL_CHOICES = [
    ('NO', 'No'),
    ('DEPRESION', 'Depresión'),
    ('ESQUIZOFRENIA', 'Esquizofrenia'),
    ('TRASTORNO_BIPOLAR', 'Trastorno bipolar'),
    ('ANSIEDAD', 'Trastorno de ansiedad'),
    ('DEMENCIA', 'Demencia'),
    ('OTRO', 'Otro'),
]

# ENFERMEDAD INFECCIOSA
ENF_INFECCIOSA_CHOICES = [
    ('NO', 'No'),
    ('HEPATITIS', 'Hepatitis'),
    ('COVID', 'COVID-19 grave'),
    ('NEUMONIA', 'Neumonía recurrente'),
    ('INFECCION_URINARIA', 'Infección urinaria recurrente'),
    ('OTRO', 'Otro'),
]

# MAL FORMACIÓN
MALFORMACION_CHOICES = [
    ('NO', 'No'),
    ('CARDIACA', 'Malformación cardíaca'),
    ('NEURAL', 'Malformación del tubo neural'),
    ('ESQUELETICA', 'Malformación esquelética'),
    ('FACIAL', 'Malformación facial'),
    ('OTRO', 'Otro'),
]

class AnamnesisGeneral(BaseModel):
    """
    Anamnesis general del paciente según ficha clínica odontológica.
    """
    
    # ✅ Relación uno a uno con Paciente
    paciente = models.OneToOneField(
        Paciente,
        on_delete=models.CASCADE,
        related_name='anamnesis_general',
        verbose_name="Paciente"
    )
    
    # ================== SECCIÓN D: ANTECEDENTES PATOLÓGICOS PERSONALES ==================
    
    # 1. ALERGIA ANTIBIÓTICO
    alergia_antibiotico = models.CharField(
        max_length=20,
        choices=ALERGIA_ANTIBIOTICO_CHOICES,
        default='NO',
        verbose_name="Alergia a antibióticos"
    )
    alergia_antibiotico_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro antibiótico"
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
        verbose_name="Especificar otro tipo de anestesia"
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
    vih_sida_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro estado VIH/SIDA"
    )
    
    # 5. TUBERCULOSIS
    tuberculosis = models.CharField(
        max_length=25,
        choices=TUBERCULOSIS_CHOICES,
        default='NO',
        verbose_name="Tuberculosis"
    )
    tuberculosis_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro estado tuberculosis"
    )
    
    # 6. ASMA
    asma = models.CharField(
        max_length=25,
        choices=ASMA_CHOICES,
        default='NO',
        verbose_name="Asma"
    )
    asma_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro tipo de asma"
    )
    
    # 7. DIABETES
    diabetes = models.CharField(
        max_length=20,
        choices=DIABETES_CHOICES,
        default='NO',
        verbose_name="Diabetes"
    )
    diabetes_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro tipo de diabetes"
    )
    
    # 8. HIPERTENSIÓN ARTERIAL
    hipertension_arterial = models.CharField(
        max_length=20,
        choices=HIPERTENSION_ARTERIAL_CHOICES,
        default='NO',
        verbose_name="Hipertensión arterial"
    )
    hipertension_arterial_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro tipo de hipertensión"
    )
    
    # 9. ENF. CARDIACA
    enfermedad_cardiaca = models.CharField(
        max_length=25,
        choices=ENF_CARDIACA_CHOICES,
        default='NO',
        verbose_name="Enfermedad cardíaca"
    )
    enfermedad_cardiaca_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otra enfermedad cardíaca"
    )
    
    # 10. OTRO (Antecedentes personales adicionales)
    otro_antecedente_personal = models.TextField(
        blank=True,
        verbose_name="Otros antecedentes personales",
        help_text="Otras enfermedades o condiciones no listadas anteriormente"
    )
    
    # ================== SECCIÓN E: ANTECEDENTES PATOLÓGICOS FAMILIARES ==================
    
    # 1. CARDIOPATÍA
    cardiopatia_familiar = models.CharField(
        max_length=20,
        choices=FAMILIAR_BASE_CHOICES,
        default='NO',
        verbose_name="Cardiopatía en familiares"
    )
    cardiopatia_familiar_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro familiar"
    )
    
    # 2. HIPERTENSIÓN ARTERIAL
    hipertension_familiar = models.CharField(
        max_length=20,
        choices=FAMILIAR_BASE_CHOICES,
        default='NO',
        verbose_name="Hipertensión arterial en familiares"
    )
    hipertension_familiar_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro familiar"
    )
    
    # 3. ENF. C. VASCULAR
    enfermedad_cerebrovascular_familiar = models.CharField(
        max_length=25,
        choices=ENF_CEREBROVASCULAR_CHOICES,
        default='NO',
        verbose_name="Enfermedad cerebrovascular en familiares"
    )
    enfermedad_cerebrovascular_familiar_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro tipo"
    )
    
    # 4. ENDÓCRINO METABÓLICO
    endocrino_metabolico_familiar = models.CharField(
        max_length=25,
        choices=ENDOCRINO_METABOLICO_CHOICES,
        default='NO',
        verbose_name="Enfermedades endocrino-metabólicas en familiares"
    )
    endocrino_metabolico_familiar_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro tipo"
    )
    
    # 5. CÁNCER
    cancer_familiar = models.CharField(
        max_length=20,
        choices=CANCER_CHOICES,
        default='NO',
        verbose_name="Cáncer en familiares"
    )
    cancer_familiar_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro tipo de cáncer"
    )
    
    # 6. TUBERCULOSIS
    tuberculosis_familiar = models.CharField(
        max_length=20,
        choices=FAMILIAR_BASE_CHOICES,
        default='NO',
        verbose_name="Tuberculosis en familiares"
    )
    tuberculosis_familiar_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro familiar"
    )
    
    # 7. ENF. MENTAL
    enfermedad_mental_familiar = models.CharField(
        max_length=25,
        choices=ENF_MENTAL_CHOICES,
        default='NO',
        verbose_name="Enfermedad mental en familiares"
    )
    enfermedad_mental_familiar_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro tipo"
    )
    
    # 8. ENF. INFECCIOSA
    enfermedad_infecciosa_familiar = models.CharField(
        max_length=25,
        choices=ENF_INFECCIOSA_CHOICES,
        default='NO',
        verbose_name="Enfermedad infecciosa en familiares"
    )
    enfermedad_infecciosa_familiar_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro tipo"
    )
    
    # 9. MAL FORMACIÓN
    malformacion_familiar = models.CharField(
        max_length=25,
        choices=MALFORMACION_CHOICES,
        default='NO',
        verbose_name="Malformación en familiares"
    )
    malformacion_familiar_otro = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Especificar otro tipo"
    )
    
    # 10. OTRO (Antecedentes familiares adicionales)
    otro_antecedente_familiar = models.TextField(
        blank=True,
        verbose_name="Otros antecedentes familiares",
        help_text="Otras enfermedades familiares no listadas anteriormente"
    )
    
    # ================== HÁBITOS ==================
    habitos = models.TextField(
        blank=True,
        verbose_name="Hábitos",
        help_text="Tabaco, alcohol, drogas, bruxismo, higiene bucal, etc."
    )
    
    # ================== OBSERVACIONES GENERALES ==================
    observaciones = models.TextField(
        blank=True,
        verbose_name="Observaciones generales",
        help_text="Cualquier información adicional relevante para la historia clínica"
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
            ('hipertension_arterial', 'hipertension_arterial_otro', 'OTRO'),
            ('enfermedad_cardiaca', 'enfermedad_cardiaca_otro', 'OTRO'),
            ('cardiopatia_familiar', 'cardiopatia_familiar_otro', 'OTRO'),
            ('hipertension_familiar', 'hipertension_familiar_otro', 'OTRO'),
            ('enfermedad_cerebrovascular_familiar', 'enfermedad_cerebrovascular_familiar_otro', 'OTRO'),
            ('endocrino_metabolico_familiar', 'endocrino_metabolico_familiar_otro', 'OTRO'),
            ('cancer_familiar', 'cancer_familiar_otro', 'OTRO'),
            ('tuberculosis_familiar', 'tuberculosis_familiar_otro', 'OTRO'),
            ('enfermedad_mental_familiar', 'enfermedad_mental_familiar_otro', 'OTRO'),
            ('enfermedad_infecciosa_familiar', 'enfermedad_infecciosa_familiar_otro', 'OTRO'),
            ('malformacion_familiar', 'malformacion_familiar_otro', 'OTRO'),
        ]
        
        for campo_select, campo_otro, valor_otro in campos_otro:
            valor_select = getattr(self, campo_select)
            valor_otro_field = getattr(self, campo_otro)
            
            if valor_select == valor_otro and not valor_otro_field:
                nombre_display = dict(self._meta.get_field(campo_select).choices).get(valor_select, valor_select)
                errors[campo_otro] = f'Debe especificar cuando selecciona "{nombre_display}"'
        
        if errors:
            raise ValidationError(errors)
    
    @property
    def tiene_condiciones_importantes(self):
        """Verifica si tiene condiciones importantes para odontología"""
        condiciones = [
            self.alergia_antibiotico != 'NO',
            self.alergia_anestesia != 'NO',
            self.hemorragias == 'SI',
            self.vih_sida not in ['NEGATIVO', 'NO_SABE'],
            self.tuberculosis not in ['NO', 'VACUNA_BCG'],
            self.diabetes != 'NO',
            self.hipertension_arterial != 'NO',
            self.enfermedad_cardiaca != 'NO',
        ]
        return any(condiciones)
    
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
        
        if self.vih_sida not in ['NEGATIVO', 'NO_SABE']:
            condiciones.append("VIH/SIDA")
        
        if self.tuberculosis not in ['NO', 'VACUNA_BCG']:
            condiciones.append("Tuberculosis")
        
        if self.diabetes != 'NO':
            condiciones.append("Diabetes")
        
        if self.hipertension_arterial != 'NO':
            condiciones.append("Hipertensión")
        
        if self.enfermedad_cardiaca != 'NO':
            condiciones.append("Enfermedad cardíaca")
        
        return ", ".join(condiciones) if condiciones else "Sin condiciones de riesgo"
    
    def save(self, *args, **kwargs):
        """Método save con validaciones automáticas"""
        self.full_clean()
        super().save(*args, **kwargs)