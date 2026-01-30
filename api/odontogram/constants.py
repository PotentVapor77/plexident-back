# api/odontogram/constans/constants.py

"""
Constantes y configuraciones del odontograma
"""
# api.odontogram.constans.constants.py
class FDIConstants:
    """Gestión centralizada de códigos FDI"""
    
    # Definición de cuadrantes y posiciones
    CUADRANTES = {
        1: {'arcada': 'SUPERIOR', 'lado': 'DERECHO', 'denticion': 'permanente'},
        2: {'arcada': 'SUPERIOR', 'lado': 'IZQUIERDO', 'denticion': 'permanente'},
        3: {'arcada': 'INFERIOR', 'lado': 'IZQUIERDO', 'denticion': 'permanente'},
        4: {'arcada': 'INFERIOR', 'lado': 'DERECHO', 'denticion': 'permanente'},
        5: {'arcada': 'SUPERIOR', 'lado': 'DERECHO', 'denticion': 'temporal'},
        6: {'arcada': 'SUPERIOR', 'lado': 'IZQUIERDO', 'denticion': 'temporal'},
        7: {'arcada': 'INFERIOR', 'lado': 'IZQUIERDO', 'denticion': 'temporal'},
        8: {'arcada': 'INFERIOR', 'lado': 'DERECHO', 'denticion': 'temporal'},
    }
    
    # Tipos de dientes en cada cuadrante
    POSICIONES_EN_CUADRANTE = {
        'permanente': {
            1: 'Incisivo central',
            2: 'Incisivo lateral',
            3: 'Canino',
            4: 'Primer premolar',
            5: 'Segundo premolar',
            6: 'Primer molar',
            7: 'Segundo molar',
            8: 'Tercer molar',
        },
        'temporal': {
            1: 'Incisivo central',
            2: 'Incisivo lateral',
            3: 'Canino',
            4: 'Primer molar',
            5: 'Segundo molar',
        }
    }
    
    # Mapeo de dientes a números 3D (1-32)
    FDI_A_NUMERO_3D = {
        '11': 1, '12': 2, '13': 3, '14': 4, '15': 5, '16': 6, '17': 7, '18': 8,
        '21': 9, '22': 10, '23': 11, '24': 12, '25': 13, '26': 14, '27': 15, '28': 16,
        '31': 17, '32': 18, '33': 19, '34': 20, '35': 21, '36': 22, '37': 23, '38': 24,
        '41': 25, '42': 26, '43': 27, '44': 28, '45': 29, '46': 30, '47': 31, '48': 32,
        # Temporales
        '51': 33, '52': 34, '53': 35, '54': 36, '55': 37,
        '61': 38, '62': 39, '63': 40, '64': 41, '65': 42,
        '71': 43, '72': 44, '73': 45, '74': 46, '75': 47,
        '81': 48, '82': 49, '83': 50, '84': 51, '85': 52,
    }
    
    @classmethod
    def generar_choices_fdi(cls):
        """
        Genera dinámicamente todos los códigos FDI válidos
        Retorna: [(codigo, label), ...]
        """
        choices = []
        
        for cuadrante, info_cuad in cls.CUADRANTES.items():
            denticion = info_cuad['denticion']
            posiciones = cls.POSICIONES_EN_CUADRANTE[denticion]
            
            for posicion, nombre_posicion in posiciones.items():
                codigo_fdi = f"{cuadrante}{posicion}"
                arcada = info_cuad['arcada']
                lado = info_cuad['lado']
                label = f"{codigo_fdi} - {nombre_posicion} ({arcada} {lado})"
                
                choices.append((codigo_fdi, label))
        
        return choices
    
    @classmethod
    def obtener_info_fdi(cls, codigo_fdi):
        """
        Extrae información del código FDI
        Retorna: {cuadrante, posicion, arcada, lado, denticion, nombre}
        """
        if not codigo_fdi or len(codigo_fdi) != 2:
            return None
        
        cuadrante = int(codigo_fdi[0])
        posicion = int(codigo_fdi[1])
        
        if cuadrante not in cls.CUADRANTES:
            return None
        
        info_cuad = cls.CUADRANTES[cuadrante]
        denticion = info_cuad['denticion']
        
        if posicion not in cls.POSICIONES_EN_CUADRANTE[denticion]:
            return None
        
        return {
            'codigo_fdi': codigo_fdi,
            'cuadrante': cuadrante,
            'posicion': posicion,
            'arcada': info_cuad['arcada'],
            'lado': info_cuad['lado'],
            'denticion': denticion,
            'nombre': cls.POSICIONES_EN_CUADRANTE[denticion][posicion],
            'numero_3d': cls.FDI_A_NUMERO_3D.get(codigo_fdi),
        }


# Instancia global con los choices precalculados
FDI_CHOICES = FDIConstants.generar_choices_fdi()
PIEZAS_INDICE_PERMANENTES = [
    '16', '11', '26',  # Superior: 1er molar derecho, incisivo central, 1er molar izquierdo
    '36', '31', '46',  # Inferior: 1er molar izquierdo, incisivo central, 1er molar derecho
]

# Piezas dentales alternativas (en caso de ausencia)
ALTERNATIVAS_PIEZAS = {
    '16': ['17', '15'],  # Si 16 ausente, usar 17, luego 15
    '11': ['21', '12'],  # Si 11 ausente, usar 21, luego 12
    '26': ['27', '25'],  # Si 26 ausente, usar 27, luego 25
    '36': ['37', '35'],  # Si 36 ausente, usar 37, luego 35
    '31': ['41', '32'],  # Si 31 ausente, usar 41, luego 32
    '46': ['47', '45'],  # Si 46 ausente, usar 47, luego 45
}

# Piezas dentales índice para dentición temporal (niños)
PIEZAS_INDICE_TEMPORALES = [
    '55', '51', '65',  # Superior: 2do molar derecho, incisivo central, 2do molar izquierdo
    '75', '71', '85',  # Inferior: 2do molar izquierdo, incisivo central, 2do molar derecho
]

# Alternativas para dentición temporal
ALTERNATIVAS_TEMPORALES = {
    '55': ['54', '53'],
    '51': ['61', '52'],
    '65': ['64', '63'],
    '75': ['74', '73'],
    '71': ['81', '72'],
    '85': ['84', '83'],
}

# ============================================================================
# ESCALAS DE PUNTUACIÓN
# ============================================================================

# Escala de placa (Índice de Placa de Silness & Löe)
ESCALA_PLACA = {
    0: 'Sin placa',
    1: 'Película de placa adherida al borde gingival libre y superficies adyacentes del diente',
    2: 'Acumulación moderada de depósitos blandos en la bolsa gingival y/o diente y margen gingival que puede verse a simple vista',
    3: 'Abundancia de materia blanda dentro de la bolsa gingival y/o en el diente y margen gingival'
}

# Escala de cálculo (Índice de Cálculo de Greene & Vermillion)
ESCALA_CALCULO = {
    0: 'Sin cálculo',
    1: 'Cálculo supragingival que cubre no más de 1/3 de la superficie expuesta',
    2: 'Cálculo supragingival que cubre más de 1/3 pero no más de 2/3 de la superficie expuesta, o presencia de cálculo subgingival en forma de tiras aisladas',
    3: 'Cálculo supragingival que cubre más de 2/3 de la superficie expuesta o banda continua de cálculo subgingival'
}

# Escala de gingivitis (Índice Gingival de Löe & Silness)
ESCALA_GINGIVITIS = {
    0: 'Encía normal',
    1: 'Leve inflamación, ligero cambio de color, ligero edema, no sangrado al sondaje',
    2: 'Moderada inflamación, enrojecimiento, edema, sangrado al sondaje',
    3: 'Inflamación severa, marcado enrojecimiento y edema, ulceración, tendencia al sangrado espontáneo'
}

# Niveles de enfermedad periodontal
NIVELES_PERIODONTAL = {
    'LEVE': 'Leve - Pérdida de inserción clínica de 1-2 mm',
    'MODERADA': 'Moderada - Pérdida de inserción clínica de 3-4 mm',
    'SEVERA': 'Severa - Pérdida de inserción clínica ≥5 mm'
}

# Tipos de oclusión
TIPOS_OCLUSION = {
    'ANGLE_I': 'Clase I de Angle - Relación molar normal',
    'ANGLE_II': 'Clase II de Angle - Distoclusión',
    'ANGLE_III': 'Clase III de Angle - Mesioclusión'
}

# Niveles de fluorosis (Índice de Dean)
NIVELES_FLUOROSIS = {
    'NINGUNA': 'Normal',
    'LEVE': 'Leve - Opacidades blanquecinas que cubren ≤25% de la superficie',
    'MODERADA': 'Moderada - Opacidades que cubren 26-50% de la superficie',
    'SEVERA': 'Severa - Opacidades que cubren >50%, con picaduras y tinción'
}

# ============================================================================
# CÁLCULO DE ÍNDICES
# ============================================================================

def calcular_ohi_s(placa_total, calculo_total, num_superficies=6):
    """
    Calcula el Índice de Higiene Oral Simplificado (OHI-S)
    OHI-S = Índice de Placa Simplificado + Índice de Cálculo Simplificado
    """
    if num_superficies == 0:
        return None
    
    indice_placa = placa_total / num_superficies
    indice_calculo = calculo_total / num_superficies
    
    return {
        'indice_placa': round(indice_placa, 2),
        'indice_calculo': round(indice_calculo, 2),
        'ohi_s': round(indice_placa + indice_calculo, 2),
        'interpretacion': interpretar_ohi_s(indice_placa + indice_calculo)
    }

def interpretar_ohi_s(valor):
    """Interpreta el valor del OHI-S"""
    if valor is None:
        return 'Sin datos'
    elif valor <= 0.6:
        return 'Excelente'
    elif valor <= 1.2:
        return 'Bueno'
    elif valor <= 1.8:
        return 'Regular'
    elif valor <= 3.0:
        return 'Deficiente'
    else:
        return 'Pésimo'

def calcular_gi_promedio(gingivitis_total, num_superficies=6):
    """
    Calcula el promedio del Índice Gingival (GI)
    """
    if num_superficies == 0:
        return None
    
    promedio = gingivitis_total / num_superficies
    return {
        'promedio': round(promedio, 2),
        'interpretacion': interpretar_gi(promedio)
    }

def interpretar_gi(valor):
    """Interpreta el valor del Índice Gingival"""
    if valor is None:
        return 'Sin datos'
    elif valor <= 0.1:
        return 'Normal'
    elif valor <= 1.0:
        return 'Gingivitis leve'
    elif valor <= 2.0:
        return 'Gingivitis moderada'
    else:
        return 'Gingivitis severa'