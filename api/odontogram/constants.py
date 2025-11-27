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
