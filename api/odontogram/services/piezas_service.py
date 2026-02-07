# api/odontogram/services/piezas_service.py

"""
Servicio para manejar la selección de piezas dentales índice
CORREGIDO: Elimina referencias a campos inexistentes (activo, pieza_reemplazada)
"""

from typing import List, Dict, Optional, Set
from venv import logger
from django.db.models import Q
from api.odontogram.models import Diente, DiagnosticoDental
from api.odontogram.constants import (
    ALTERNATIVAS_PIEZAS,
    ALTERNATIVAS_TEMPORALES,
    PIEZAS_INDICE_PERMANENTES,
    PIEZAS_INDICE_TEMPORALES
)
from api.patients.models.paciente import Paciente


class PiezasIndiceService:
    """
    Servicio para gestionar piezas índice en indicadores de salud bucal
    """
    
    # Piezas principales según índice OHI-S
    PIEZAS_PRINCIPALES = ['16', '11', '26', '36', '31', '46']
    
    # Alternativas si las principales no están disponibles
    ALTERNATIVAS = {
        '16': '17',  
        '11': '21',  
        '26': '27',  
        '36': '37',  
        '31': '41',  
        '46': '47',  
    }
    
    DIAGNOSTICOS_NO_DISPONIBLE = [
        'ausente',
        'perdida_caries',
        'perdida_otra_causa',
        'extraccion_indicada',
        'extraccion_otra_causa',
    ]
    
    @staticmethod
    def determinar_denticion_paciente(paciente_id: str) -> str:
        """
        Determina si el paciente tiene dentición permanente o temporal
        basándose en los dientes presentes en su odontograma.
        
        Args:
            paciente_id: UUID del paciente
            
        Returns:
            'permanente', 'temporal' o 'mixta'
        """
        # Obtener todos los dientes del paciente (no ausentes)
        dientes = Diente.objects.filter(
            paciente_id=paciente_id,
            ausente=False
        ).values_list('codigo_fdi', flat=True)
        
        if not dientes:
            # Si no hay dientes, asumir permanente por defecto
            return 'permanente'
        
        # Códigos FDI para dientes temporales (deciduos)
        # Cuadrantes 5 y 6 (superiores), 7 y 8 (inferiores)
        codigos_temporales = {
            '51', '52', '53', '54', '55',  # Cuadrante 5
            '61', '62', '63', '64', '65',  # Cuadrante 6
            '71', '72', '73', '74', '75',  # Cuadrante 7
            '81', '82', '83', '84', '85',  # Cuadrante 8
        }
        
        # Códigos FDI para dientes permanentes
        # Cuadrantes 1 y 2 (superiores), 3 y 4 (inferiores)
        codigos_permanentes = {
            '11', '12', '13', '14', '15', '16', '17', '18',  # Cuadrante 1
            '21', '22', '23', '24', '25', '26', '27', '28',  # Cuadrante 2
            '31', '32', '33', '34', '35', '36', '37', '38',  # Cuadrante 3
            '41', '42', '43', '44', '45', '46', '47', '48',  # Cuadrante 4
        }
        
        # Contar cuántos dientes de cada tipo tiene el paciente
        dientes_temporales = sum(1 for d in dientes if d in codigos_temporales)
        dientes_permanentes = sum(1 for d in dientes if d in codigos_permanentes)
        
        # Determinar dentición
        if dientes_temporales > 0 and dientes_permanentes > 0:
            return 'mixta'
        elif dientes_temporales > dientes_permanentes:
            return 'temporal'
        else:
            return 'permanente'
    
    @classmethod
    def _pieza_esta_disponible(cls, diente: Diente) -> bool:
        """
        
        Una pieza NO está disponible si:
        1. Tiene el flag ausente=True
        2. Tiene diagnósticos que indican pérdida/extracción
        
        Args:
            diente: Instancia del modelo Diente
            
        Returns:
            bool: True si está disponible, False si no
        """
        # Verificación 1: Flag de ausente
        if diente.ausente:
            logger.debug(f"Pieza {diente.codigo_fdi} marcada como ausente")
            return False
        
        # Verificación 2: Diagnósticos que invalidan
        diagnosticos_invalidantes = DiagnosticoDental.objects.filter(
            superficie__diente=diente,
            diagnostico_catalogo__key__in=cls.DIAGNOSTICOS_NO_DISPONIBLE,
            activo=True
        ).exists()
        
        if diagnosticos_invalidantes:
            logger.debug(
                f"Pieza {diente.codigo_fdi} tiene diagnósticos invalidantes"
            )
            return False
        
        # Si pasó ambas verificaciones, está disponible
        return True
    
    @staticmethod
    def obtener_dientes_excluidos(paciente_id: str) -> Set[str]:
        """
        Obtiene los códigos FDI de dientes que tienen diagnósticos
        que los excluyen de ser usados como piezas índice.
        
        Args:
            paciente_id: UUID del paciente
            
        Returns:
            Set de códigos FDI excluidos
        """
        try:
            # Obtener diagnósticos aplicados que excluyen piezas
            diagnosticos_excluidos = DiagnosticoDental.objects.filter(
                superficie__diente__paciente_id=paciente_id,
                diagnostico_catalogo__key__in=PiezasIndiceService.DIAGNOSTICOS_EXCLUSION
            ).select_related('superficie__diente').values_list(
                'superficie__diente__codigo_fdi', 
                flat=True
            )
            
            return set(diagnosticos_excluidos)
        except Exception as e:
            # Si hay error, retornar set vacío
            return set()
    
    @staticmethod
    def es_pieza_disponible(diente: Diente, dientes_excluidos: Set[str]) -> bool:
        """
        Verifica si una pieza dental está disponible para ser usada como índice.
        
        Args:
            diente: Instancia del modelo Diente
            dientes_excluidos: Set de códigos FDI excluidos
            
        Returns:
            True si está disponible, False en caso contrario
        """
        # No disponible si está ausente
        if diente.ausente:
            return False
        
        # No disponible si tiene diagnóstico de exclusión
        if diente.codigo_fdi in dientes_excluidos:
            return False
        
        return True
    
    @staticmethod
    def obtener_piezas_indice(paciente_id: str, denticion: Optional[str] = None) -> List[str]:
        """
        Obtiene la lista de piezas índice apropiadas para el paciente
        
        Args:
            paciente_id: UUID del paciente
            denticion: 'permanente' o 'temporal' (opcional)
            
        Returns:
            Lista de códigos FDI de piezas índice
        """
        if denticion is None:
            denticion = PiezasIndiceService.determinar_denticion_paciente(paciente_id)
        
        if denticion == 'temporal':
            return PIEZAS_INDICE_TEMPORALES
        else:
            return PIEZAS_INDICE_PERMANENTES
    
    @staticmethod
    def buscar_pieza_disponible(
        paciente_id: str, 
        pieza_objetivo: str, 
        alternativas: List[str],
        dientes_excluidos: Set[str]
    ) -> Optional[Dict]:
        """
        Busca una pieza dental disponible, probando alternativas si la principal no existe
        
        Args:
            paciente_id: UUID del paciente
            pieza_objetivo: Código FDI de la pieza principal a buscar
            alternativas: Lista de códigos FDI alternativos
            dientes_excluidos: Set de códigos FDI excluidos
            
        Returns:
            Dict con información de la pieza encontrada o None
        """
        # Primero buscar la pieza objetivo
        diente = Diente.objects.filter(
            paciente_id=paciente_id,
            codigo_fdi=pieza_objetivo,
        ).first()
        
        if diente and PiezasIndiceService.es_pieza_disponible(diente, dientes_excluidos):
            return {
                'codigo_fdi': pieza_objetivo,
                'diente': diente,
                'es_alternativa': False,
                'alternativas_probadas': []
            }
        
        # Si no existe o no está disponible, probar alternativas
        alternativas_probadas = []
        for alternativa in alternativas:
            alternativas_probadas.append(alternativa)
            
            diente = Diente.objects.filter(
                paciente_id=paciente_id,
                codigo_fdi=alternativa,
            ).first()
            
            if diente and PiezasIndiceService.es_pieza_disponible(diente, dientes_excluidos):
                return {
                    'codigo_fdi': alternativa,
                    'diente': diente,
                    'es_alternativa': True,
                    'alternativas_probadas': alternativas_probadas
                }
        
        # No se encontró ninguna pieza disponible
        return None
    
    @staticmethod
    def obtener_mapa_piezas_disponibles(paciente_id: str) -> Dict:
        """
        Obtiene un mapa completo de piezas índice disponibles para el paciente
        
        Args:
            paciente_id: UUID del paciente
            
        Returns:
            Diccionario con información de cada pieza índice
        """
        denticion = PiezasIndiceService.determinar_denticion_paciente(paciente_id)
        piezas_indice = PiezasIndiceService.obtener_piezas_indice(paciente_id, denticion)
        
        # Obtener dientes excluidos (con diagnósticos de exclusión)
        dientes_excluidos = PiezasIndiceService.obtener_dientes_excluidos(paciente_id)
        
        if denticion == 'temporal':
            mapa_alternativas = ALTERNATIVAS_TEMPORALES
        else:
            mapa_alternativas = ALTERNATIVAS_PIEZAS
        
        resultado = {}
        
        for pieza in piezas_indice:
            alternativas = mapa_alternativas.get(pieza, [])
            
            pieza_disponible = PiezasIndiceService.buscar_pieza_disponible(
                paciente_id, pieza, alternativas, dientes_excluidos
            )
            
            if pieza_disponible:
                resultado[pieza] = {
                    'codigo_original': pieza,
                    'codigo_usado': pieza_disponible['codigo_fdi'],
                    'diente_id': str(pieza_disponible['diente'].id) if pieza_disponible['diente'] else None,
                    'es_alternativa': pieza_disponible['es_alternativa'],
                    'disponible': True,
                    'ausente': False
                }
            else:
                resultado[pieza] = {
                    'codigo_original': pieza,
                    'codigo_usado': None,
                    'diente_id': None,
                    'es_alternativa': False,
                    'disponible': False,
                    'ausente': True
                }
        
        return resultado
    
    @classmethod
    def obtener_informacion_piezas(cls, paciente_id: str) -> Dict:
        """
        Obtiene información de piezas dentales para indicadores,
        verificando correctamente la disponibilidad.
        
        Args:
            paciente_id: UUID del paciente
            
        Returns:
            Dict con información estructurada de piezas
        """
        from datetime import date
        
        try:
            paciente = Paciente.objects.get(id=paciente_id)
        except Paciente.DoesNotExist:
            raise ValueError(f"Paciente {paciente_id} no encontrado")
        
        # Determinar dentición basada en edad
        edad = (date.today() - paciente.fecha_nacimiento).days // 365
        denticion = 'permanente' if edad >= 12 else 'temporal'
        
        # Obtener todos los dientes del paciente con información relevante
        dientes = Diente.objects.filter(
            paciente_id=paciente_id
        ).select_related('paciente').prefetch_related(
            'superficies__diagnosticos__diagnostico_catalogo'
        )
        
        # Crear diccionario para acceso rápido
        dientes_dict = {d.codigo_fdi: d for d in dientes}
        
        # Definir las 6 piezas índice principales
        PIEZAS_INDICE_PRINCIPALES = ['16', '11', '26', '36', '31', '46']
        
        # Definir alternativas (si la principal no está disponible)
        # Nota: En la práctica dental, cuando una pieza índice no está disponible,
        # se usa la pieza adyacente del mismo tipo (ej: si 16 no está, usar 17)
        ALTERNATIVAS = {
            '16': '17',  # Si 16 no disponible, usar 17 (2do molar superior derecho)
            '11': '21',  # Si 11 no disponible, usar 12 (incisivo lateral superior derecho)
            '26': '27',  # Si 26 no disponible, usar 27 (2do molar superior izquierdo)
            '36': '37',  # Si 36 no disponible, usar 37 (2do molar inferior izquierdo)
            '31': '41',  # Si 31 no disponible, usar 32 (incisivo lateral inferior izquierdo)
            '46': '47',  # Si 46 no disponible, usar 47 (2do molar inferior derecho)
        }
        
        # Diagnósticos que hacen que una pieza no sea disponible
        DIAGNOSTICOS_NO_DISPONIBLE = [
            'ausente',
            'perdida_caries',
            'perdida_otra_causa',
            'extraccion_indicada',
            'extraccion_realizada'
        ]
        
        # Procesar cada pieza índice principal
        piezas_mapeo = {}
        stats = {
            'total_piezas': len(PIEZAS_INDICE_PRINCIPALES),
            'piezas_originales': 0,
            'piezas_alternativas': 0,
            'piezas_no_disponibles': 0,
            'piezas_disponibles': 0,
        }
        
        for codigo_original in PIEZAS_INDICE_PRINCIPALES:
            diente_original = dientes_dict.get(codigo_original)
            
            # Verificar si la pieza original está disponible
            original_disponible = cls._verificar_disponibilidad_diente(diente_original)
            
            if original_disponible['disponible']:
                # Pieza original disponible
                piezas_mapeo[codigo_original] = {
                    'codigo_usado': codigo_original,
                    'es_alternativa': False,
                    'disponible': True,
                    'codigo_original': codigo_original,
                    'diente_id': str(diente_original.id) if diente_original else None,
                    'ausente': diente_original.ausente if diente_original else False,
                    'motivo': 'Disponible',
                    'tipo': 'Original'
                }
                stats['piezas_originales'] += 1
                stats['piezas_disponibles'] += 1
                
            else:
                # Pieza original no disponible, buscar alternativa
                codigo_alternativa = ALTERNATIVAS.get(codigo_original)
                diente_alternativa = dientes_dict.get(codigo_alternativa) if codigo_alternativa else None
                alternativa_disponible = cls._verificar_disponibilidad_diente(diente_alternativa)
                
                if alternativa_disponible['disponible']:
                    # Alternativa disponible
                    piezas_mapeo[codigo_original] = {
                        'codigo_usado': codigo_alternativa,
                        'es_alternativa': True,
                        'disponible': True,
                        'codigo_original': codigo_original,
                        'diente_id': str(diente_alternativa.id) if diente_alternativa else None,
                        'ausente': diente_alternativa.ausente if diente_alternativa else False,
                        'motivo_original_no_disponible': original_disponible['motivo'],
                        'motivo': f"Usando alternativa {codigo_alternativa} porque {codigo_original} no disponible",
                        'tipo': 'Alternativa'
                    }
                    stats['piezas_alternativas'] += 1
                    stats['piezas_disponibles'] += 1
                    
                else:
                    # Ni original ni alternativa disponibles
                    piezas_mapeo[codigo_original] = {
                        'codigo_usado': None,
                        'es_alternativa': False,
                        'disponible': False,
                        'codigo_original': codigo_original,
                        'diente_id': None,
                        'ausente': True,
                        'motivo_original_no_disponible': original_disponible['motivo'],
                        'motivo_alternativa_no_disponible': alternativa_disponible['motivo'] if codigo_alternativa else 'Sin alternativa definida',
                        'motivo': f"Ni {codigo_original} ni su alternativa {codigo_alternativa} están disponibles",
                        'tipo': 'No disponible'
                    }
                    stats['piezas_no_disponibles'] += 1
        
        # Calcular porcentajes
        stats['porcentaje_disponible'] = (
            (stats['piezas_disponibles'] / stats['total_piezas']) * 100
            if stats['total_piezas'] > 0 else 0
        )
        
        # Determinar si se pueden crear indicadores
        puede_crear_indicadores = stats['piezas_disponibles'] >= 3
        
        # Generar mensaje resumen
        mensaje_resumen = cls._generar_mensaje_resumen(stats)
        
        return {
            'denticion': denticion,
            'piezas_mapeo': piezas_mapeo,
            'estadisticas': stats,
            'puede_crear_indicadores': puede_crear_indicadores,
            'mensaje': mensaje_resumen,
            'edad_paciente': edad,
            'paciente_nombre': f"{paciente.nombres} {paciente.apellidos}"
        }
    
    @classmethod
    def _verificar_disponibilidad_diente(cls, diente: Optional[Diente]) -> Dict:
        """
        Verifica si un diente está disponible para ser usado como pieza índice.
        
        Args:
            diente: Instancia de Diente (puede ser None)
            
        Returns:
            Dict con 'disponible' (bool) y 'motivo' (str)
        """
        if diente is None:
            return {'disponible': False, 'motivo': 'Diente no existe en odontograma'}
        
        if diente.ausente:
            return {'disponible': False, 'motivo': f'Diente {diente.codigo_fdi} marcado como ausente'}
        
        # Verificar diagnósticos invalidantes
        diagnosticos_invalidantes = DiagnosticoDental.objects.filter(
            superficie__diente=diente,
            diagnostico_catalogo__key__in=[
                'ausente',
                'perdida_caries',
                'perdida_otra_causa',
                'extraccion_indicada',
                'extraccion_realizada'
            ],
            activo=True
        ).exists()
        
        if diagnosticos_invalidantes:
            return {'disponible': False, 'motivo': f'Diente {diente.codigo_fdi} tiene diagnóstico que lo hace no disponible'}
        
        # Verificar movilidad severa (grado 3 o 4)
        if diente.movilidad and diente.movilidad >= 3:
            return {'disponible': False, 'motivo': f'Diente {diente.codigo_fdi} tiene movilidad severa (grado {diente.movilidad})'}
        
        # Diente disponible
        return {'disponible': True, 'motivo': 'Diente disponible'}
    @classmethod
    def _generar_mensaje_resumen(cls, stats: Dict) -> str:
        """
        Genera un mensaje resumen sobre las piezas disponibles.
        """
        if stats['piezas_disponibles'] == stats['total_piezas']:
            return "✓ Todas las piezas índice están disponibles para evaluación."
        
        elif stats['piezas_disponibles'] >= 3:
            return (
                f"✓ {stats['piezas_disponibles']} de {stats['total_piezas']} piezas disponibles "
                f"({stats['piezas_originales']} originales, {stats['piezas_alternativas']} alternativas). "
                "Suficientes para cálculos válidos."
            )
        
        else:
            return (
                f"✗ Solo {stats['piezas_disponibles']} piezas disponibles "
                f"(se requieren mínimo 3). "
                f"{stats['piezas_no_disponibles']} piezas no están disponibles."
            )
    
    @classmethod
    def _obtener_motivo_no_disponible(cls, diente: Optional[Diente]) -> str:
        """
        
        Args:
            diente: Instancia de Diente (puede ser None)
            
        Returns:
            str: Descripción del motivo
        """
        if not diente:
            return "Pieza no registrada en odontograma"
        
        if diente.ausente:
            return "Marcada como ausente"
        
        # Buscar diagnósticos invalidantes
        diagnostico_invalidante = DiagnosticoDental.objects.filter(
            superficie__diente=diente,
            diagnostico_catalogo__key__in=cls.DIAGNOSTICOS_NO_DISPONIBLE,
            activo=True
        ).select_related('diagnostico_catalogo').first()
        
        if diagnostico_invalidante:
            return f"Diagnóstico: {diagnostico_invalidante.diagnostico_catalogo.nombre}"
        
        return "Razón desconocida"
    
    @staticmethod
    def _buscar_pieza_disponible(pieza_original: str, candidatos: list, dientes_dict: dict) -> dict:
        """
        Busca una pieza disponible en la lista de candidatos
        
        CORREGIDO: No verifica 'pieza_reemplazada'
        
        Args:
            pieza_original: Código FDI de la pieza original
            candidatos: Lista de códigos FDI candidatos (original + alternativas)
            dientes_dict: Diccionario de dientes del paciente
            
        Returns:
            dict con información de la pieza seleccionada
        """
        for i, codigo in enumerate(candidatos):
            diente = dientes_dict.get(codigo)
            
            # CORREGIDO: Solo verificar si existe y no está ausente
            if diente and not diente['ausente']:
                # Pieza encontrada y disponible
                return {
                    'codigo_usado': codigo,
                    'es_alternativa': i > 0,  # Es alternativa si no es el primer candidato
                    'disponible': True,
                    'codigo_original': pieza_original,
                    'diente_id': str(diente['id']),
                    'ausente': False
                }
        
        # No se encontró ninguna pieza disponible
        return {
            'codigo_usado': None,
            'es_alternativa': False,
            'disponible': False,
            'codigo_original': pieza_original,
            'diente_id': None,
            'ausente': True
        }
    
    @staticmethod
    def verificar_disponibilidad(paciente_id: str) -> dict:
        """
        Verifica si hay suficientes piezas dentales disponibles para crear
        indicadores de salud bucal válidos.
        
        Args:
            paciente_id: UUID del paciente
            
        Returns:
            dict con información de disponibilidad
        """
        info_piezas = PiezasIndiceService.obtener_informacion_piezas(paciente_id)
        
        piezas_disponibles = (
            info_piezas['estadisticas']['piezas_originales'] + 
            info_piezas['estadisticas']['piezas_alternativas']
        )
        
        # Se requieren al menos 3 piezas para cálculos válidos
        puede_crear = piezas_disponibles >= 3
        
        if puede_crear:
            mensaje = f"Puede crear indicadores. {piezas_disponibles} piezas disponibles."
        else:
            mensaje = (
                f"No hay suficientes piezas dentales disponibles. "
                f"Se requieren al menos 3 piezas, solo hay {piezas_disponibles} disponibles."
            )
        
        return {
            'puede_crear_indicadores': puede_crear,
            'piezas_disponibles': piezas_disponibles,
            'mensaje': mensaje,
            'denticion': info_piezas['denticion'],
            'estadisticas': info_piezas['estadisticas']
        }