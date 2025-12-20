# patients/models/constants.py
# Opciones comunes para todos los modelos

SEXOS = [
    ('M', 'Masculino'),
    ('F', 'Femenino'),
    ('O', 'Otro'),
]

CONDICION_EDAD = [
    ('H', 'Horas'),
    ('D', 'Días'),
    ('M', 'Meses'),
    ('A', 'Años'),
]

EMBARAZADA_CHOICES = [
    ('SI', 'Sí'),
    ('NO', 'No'),
]

# Sección D: ANTECEDENTES PATOLÓGICOS PERSONALES - Opciones
ALERGIA_TIPO = [
    ('ANTIBIOTICO', 'Antibiótico'),
    ('ANESTESIA', 'Anestesia'),
    ('NINGUNA', 'Ninguna'),
    ('OTRO', 'Otro'),
]

HEMORRAGIAS_CHOICES = [
    ('SI', 'Sí'),
    ('NO', 'No'),
]

VIH_SIDA_CHOICES = [
    ('POSITIVO', 'Positivo'),
    ('NEGATIVO', 'Negativo'),
    ('NO_SABE', 'No sabe'),
]

TUBERCULOSIS_CHOICES = [
    ('ACTIVA', 'Activa'),
    ('TRATADA', 'Tratada'),
    ('NUNCA', 'Nunca'),
    ('NO_SABE', 'No sabe'),
]

ASMA_CHOICES = [
    ('LEVE', 'Leve intermitente'),
    ('MODERADA', 'Moderada persistente'),
    ('SEVERA', 'Severa persistente'),
    ('NO', 'No tiene'),
]

DIABETES_CHOICES = [
    ('TIPO1', 'Tipo 1'),
    ('TIPO2', 'Tipo 2'),
    ('GESTACIONAL', 'Gestacional'),
    ('NO', 'No tiene'),
]

HIPERTENSION_CHOICES = [
    ('CONTROLADA', 'Controlada'),
    ('NO_CONTROLADA', 'No controlada'),
    ('NO', 'No tiene'),
]

ENFERMEDAD_CARDIACA_CHOICES = [
    ('CONGENITA', 'Congénita'),
    ('ADQUIRIDA', 'Adquirida'),
    ('NO', 'No tiene'),
]

# Sección E: ANTECEDENTES PATOLÓGICOS FAMILIARES - Opciones
CARDIOPATIA_FAMILIAR_CHOICES = [
    ('PADRE', 'Padre'),
    ('MADRE', 'Madre'),
    ('HERMANOS', 'Hermanos'),
    ('ABUELOS', 'Abuelos'),
    ('NO', 'No hay antecedentes'),
]

HIPERTENSION_FAMILIAR_CHOICES = [
    ('PADRE', 'Padre'),
    ('MADRE', 'Madre'),
    ('HERMANOS', 'Hermanos'),
    ('ABUELOS', 'Abuelos'),
    ('NO', 'No hay antecedentes'),
]

ENFERMEDAD_VASCULAR_CHOICES = [
    ('PADRE', 'Padre'),
    ('MADRE', 'Madre'),
    ('HERMANOS', 'Hermanos'),
    ('ABUELOS', 'Abuelos'),
    ('NO', 'No hay antecedentes'),
]

CANCER_FAMILIAR_CHOICES = [
    ('PADRE', 'Padre'),
    ('MADRE', 'Madre'),
    ('HERMANOS', 'Hermanos'),
    ('ABUELOS', 'Abuelos'),
    ('NO', 'No hay antecedentes'),
]

ENFERMEDAD_MENTAL_CHOICES = [
    ('PADRE', 'Padre'),
    ('MADRE', 'Madre'),
    ('HERMANOS', 'Hermanos'),
    ('ABUELOS', 'Abuelos'),
    ('NO', 'No hay antecedentes'),
]

# Sección G: EXAMEN DEL SISTEMA ESTOMATOGNÁTICO - Estados
ESTADO_EXAMEN = [
    ('NORMAL', 'Normal'),
    ('ANORMAL', 'Anormal'),
    ('NO_EXAMINADO', 'No examinado'),
]