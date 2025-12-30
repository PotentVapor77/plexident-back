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
    ('SI', 'Si'),
    ('NO', 'No'),
]


# Sección D: ANTECEDENTES PATOLÓGICOS PERSONALES - Opciones
ALERGIA_ANTIBIOTICO_CHOICES = [
    ('NO', 'No'),
    ('PENICILINA', 'Penicilina'),
    ('SULFA', 'Sulfa'),
    ('OTRO', 'Otro'),
]

ALERGIA_ANESTESIA_CHOICES = [
    ('NO', 'No'),
    ('LOCAL', 'Anestesia local'),
    ('GENERAL', 'Anestesia general'),
    ('AMBAS', 'Ambas'),
    ('OTRO', 'Otro'),
]

# 3. HEMORRAGIAS - Simple: Sí o No (si no sabe, marca No por defecto)
HEMORRAGIAS_CHOICES = [
    ('NO', 'No'),
    ('SI', 'Sí'),
]

# 4. VIH / SIDA - Aquí SÍ tiene sentido "Desconocido" (no se ha hecho la prueba)
VIH_SIDA_CHOICES = [
    ('NEGATIVO', 'Negativo'),
    ('POSITIVO', 'Positivo'),
    ('DESCONOCIDO', 'No se ha realizado prueba'),
]

# 5. TUBERCULOSIS - "Desconocido" útil (puede no recordar diagnóstico antiguo)
TUBERCULOSIS_CHOICES = [
    ('NUNCA', 'Nunca'),
    ('TRATADA', 'Tratada anteriormente'),
    ('ACTIVA', 'Activa'),
    ('DESCONOCIDO', 'No está seguro'),
]

# 6. ASMA - Sin desconocido (si tiene síntomas respiratorios, el médico evalúa)
ASMA_CHOICES = [
    ('NO', 'No'),
    ('LEVE', 'Leve'),
    ('MODERADA', 'Moderada'),
    ('SEVERA', 'Severa'),
]

# 7. DIABETES - Sin desconocido (se diagnostica con exámenes)
DIABETES_CHOICES = [
    ('NO', 'No'),
    ('PREDIABETICO', 'Prediabético'),
    ('TIPO_1', 'Tipo 1'),
    ('TIPO_2', 'Tipo 2'),
    ('GESTACIONAL', 'Gestacional'),
]

# 8. HIPERTENSIÓN - Sin desconocido (se mide en consulta)
HIPERTENSION_CHOICES = [
    ('NO', 'No'),
    ('CONTROLADA', 'Controlada'),
    ('NO_CONTROLADA', 'No controlada'),
    ('SIN_TRATAMIENTO', 'Sin tratamiento'),
]

# 9. ENFERMEDAD CARDÍACA - "Otra" cubre casos no listados
ENFERMEDAD_CARDIACA_CHOICES = [
    ('NO', 'No'),
    ('ARRITMIA', 'Arritmia'),
    ('INSUFICIENCIA', 'Insuficiencia cardíaca'),
    ('CONGENITA', 'Congénita'),
    ('OTRA', 'Otra'),
]



# Sección E: ANTECEDENTES PATOLÓGICOS FAMILIARES - Opciones
FAMILIAR_BASE_CHOICES = [
    ('PADRE', 'Padre'),
    ('MADRE', 'Madre'),
    ('HERMANOS', 'Hermanos'),
    ('ABUELOS', 'Abuelos'),
    ('NO', 'No hay antecedentes'),
]

CARDIOPATIA_FAMILIAR_CHOICES = FAMILIAR_BASE_CHOICES
HIPERTENSION_FAMILIAR_CHOICES = FAMILIAR_BASE_CHOICES
ENFERMEDAD_VASCULAR_CHOICES = FAMILIAR_BASE_CHOICES
CANCER_FAMILIAR_CHOICES = FAMILIAR_BASE_CHOICES
ENFERMEDAD_MENTAL_CHOICES = FAMILIAR_BASE_CHOICES

# Sección G: EXAMEN DEL SISTEMA ESTOMATOGNÁTICO - Estados
ESTADO_EXAMEN = [
    ('NORMAL', 'Normal'),
    ('ANORMAL', 'Anormal'),
    ('NO_EXAMINADO', 'No examinado'),
]