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


# ================== ANTECEDENTES PERSONALES ==================

# ALERGIA ANTIBIÓTICO
ALERGIA_ANTIBIOTICO_CHOICES = [
    ('NO', 'No'),
    ('PENICILINA', 'Penicilina/Amoxicilina'), 
    ('SULFA', 'Sulfametoxazol/Bactrim'),      
    ('CEFALOSPORINAS', 'Cefalosporinas'),    
    ('MACROLIDOS', 'Macrólidos (Eritromicina)'),
    ('OTRO', 'Otro antibiótico'),  
]

# ALERGIA ANESTESIA
ALERGIA_ANESTESIA_CHOICES = [
    ('NO', 'No'),
    ('LOCAL', 'Anestesia local'),
    ('GENERAL', 'Anestesia general'),
    ('AMBAS', 'Ambas'),
    ('OTRO', 'Otro tipo de anestesia'),  #
]

# HEMORRAGIAS
HEMORRAGIAS_CHOICES = [
    ('NO', 'No'),
    ('SI', 'Sí'),
]

# VIH / SIDA
VIH_SIDA_CHOICES = [
    ('NEGATIVO', 'Negativo'),
    ('POSITIVO', 'Positivo'),
    ('DESCONOCIDO', 'No se ha realizado prueba'),
    ('OTRO', 'Otra condición inmunológica'),  
]

# TUBERCULOSIS
TUBERCULOSIS_CHOICES = [
    ('NUNCA', 'Nunca'),
    ('TRATADA', 'Tratada anteriormente'),
    ('ACTIVA', 'Activa'),
    ('DESCONOCIDO', 'No está seguro'),
    ('OTRO', 'Otra enfermedad pulmonar'),  
]

# ASMA
ASMA_CHOICES = [
    ('NO', 'No'),
    ('LEVE', 'Leve'),
    ('MODERADA', 'Moderada'),
    ('SEVERA', 'Severa'),
    ('OTRO', 'Otra enfermedad respiratoria'),  
]

# DIABETES
DIABETES_CHOICES = [
    ('NO', 'No'),
    ('PREDIABETICO', 'Prediabético'),
    ('TIPO_1', 'Tipo 1'),
    ('TIPO_2', 'Tipo 2'),
    ('GESTACIONAL', 'Gestacional'),
    ('OTRO', 'Otro tipo de diabetes'), 
]

# HIPERTENSIÓN ARTERIAL
HIPERTENSION_CHOICES = [
    ('NO', 'No'),
    ('CONTROLADA', 'Controlada'),
    ('NO_CONTROLADA', 'No controlada'),
    ('SIN_TRATAMIENTO', 'Sin tratamiento'),
    ('OTRO', 'Otro trastorno cardiovascular'),  
]

# ENFERMEDAD CARDIACA
ENFERMEDAD_CARDIACA_CHOICES = [
    ('NO', 'No'),
    ('ARRITMIA', 'Arritmia'),
    ('INSUFICIENCIA', 'Insuficiencia cardíaca'),
    ('CONGENITA', 'Congénita'),
    ('OTRO', 'Otra enfermedad cardíaca'),  
]

# ================== ANTECEDENTES FAMILIARES ==================

FAMILIAR_BASE_CHOICES = [
    ('NO', 'No hay antecedentes'),
    ('PADRE', 'Padre'),
    ('MADRE', 'Madre'),
    ('HERMANOS', 'Hermanos'),
    ('ABUELOS', 'Abuelos'),
    ('OTRO', 'Otro'),
]

TIPO_CANCER_CHOICES = [
    ('MAMA', 'Cáncer de Mama'),
    ('PULMON', 'Cáncer de Pulmón'),
    ('PROSTATA', 'Cáncer de Próstata'),
    ('COLORRECTAL', 'Cáncer Colorrectal'),
    ('CERVICOUTERINO', 'Cáncer Cervicouterino'),
    ('OTRO', 'Otro'),
]

# ================== EXÁMENES COMPLEMENTARIOS ==================

INFORME_EXAMENES_CHOICES = [
    ('NINGUNO', 'Ninguno'),
    ('BIOMETRIA', 'Biometría'),
    ('QUIMICA_SANGUINEA', 'Química sanguínea'),
    ('RAYOS_X', 'Rayos X'),
    ('OTROS', 'Otros'),
]

PEDIDO_EXAMENES_CHOICES = [
    ('NO', 'No'),
    ('SI', 'Sí'),
]