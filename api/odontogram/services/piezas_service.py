# api/odontogram/services/piezas_service.py

"""
Servicio para manejar la selección de piezas dentales índice
"""

from typing import List, Dict, Optional, Set
from django.db.models import Q
from api.odontogram.models import Diente, DiagnosticoDental
from api.odontogram.constants import (
    ALTERNATIVAS_PIEZAS,
    ALTERNATIVAS_TEMPORALES,
    PIEZAS_INDICE_PERMANENTES,
    PIEZAS_INDICE_TEMPORALES
)


class PiezasIndiceService:
    """
    Servicio para determinar qué piezas dentales usar como índices
    """
    
    # Diagnósticos que hacen que una pieza NO esté disponible
    DIAGNOSTICOS_EXCLUSION = [
        'ausente',                      # Ausente
        'perdida_caries',               # Perdida por Caries
        'perdida_otra_causa',           # Perdida por Otra Causa
        'extraccion_indicada',          # Extracción Indicada
        'extraccion_otra_causa',        # Extracción por Otra Causa
    ]
    
    @staticmethod
    def determinar_denticion_paciente(paciente_id: str) -> str:
        """
        Determina si el paciente tiene dentición permanente o temporal
        basándose en los dientes presentes en su odontograma.
        
        Args:
            paciente_id: UUID del paciente
            
        Returns:
            'permanente' o 'temporal'
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
        
        # Si tiene más dientes temporales, es dentición temporal
        # Si tiene más permanentes, es dentición permanente
        # En caso de mezcla (dentición mixta), priorizar permanente
        if dientes_temporales > dientes_permanentes:
            return 'temporal'
        else:
            return 'permanente'
    
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
        # Obtener diagnósticos aplicados que excluyen piezas
        # NOTA: El campo se llama 'diagnostico_catalogo' no 'diagnostico'
        diagnosticos_excluidos = DiagnosticoDental.objects.filter(
            superficie__diente__paciente_id=paciente_id,
            diagnostico_catalogo__key__in=PiezasIndiceService.DIAGNOSTICOS_EXCLUSION,
            activo=True
        ).select_related('superficie__diente').values_list(
            'superficie__diente__codigo_fdi', 
            flat=True
        )
        
        return set(diagnosticos_excluidos)
    
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
        
        # Si ninguna está disponible
        return None
    
    @staticmethod
    def obtener_piezas_disponibles(paciente_id: str) -> Dict[str, Dict]:
        """
        Obtiene todas las piezas índice disponibles para el paciente
        
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
    
    @staticmethod
    def obtener_informacion_piezas(paciente_id: str) -> Dict:
        """
        Obtiene información completa sobre las piezas índice del paciente,
        incluyendo estadísticas y alternativas usadas.
        
        Args:
            paciente_id: UUID del paciente
            
        Returns:
            Dict con dentición, piezas disponibles y estadísticas
        """
        piezas_disponibles = PiezasIndiceService.obtener_piezas_disponibles(paciente_id)
        
        # Contar estadísticas
        total_piezas = len(piezas_disponibles)
        piezas_originales = sum(
            1 for p in piezas_disponibles.values() 
            if not p['es_alternativa'] and p['disponible']
        )
        piezas_alternativas = sum(
            1 for p in piezas_disponibles.values() 
            if p['es_alternativa']
        )
        piezas_no_disponibles = sum(
            1 for p in piezas_disponibles.values() 
            if not p['disponible']
        )
        
        # Obtener dentición
        denticion = PiezasIndiceService.determinar_denticion_paciente(paciente_id)
        
        return {
            'denticion': denticion,
            'piezas': piezas_disponibles,
            'estadisticas': {
                'total_piezas': total_piezas,
                'piezas_originales': piezas_originales,
                'piezas_alternativas': piezas_alternativas,
                'piezas_no_disponibles': piezas_no_disponibles,
                'porcentaje_disponible': round(
                    (piezas_originales + piezas_alternativas) / total_piezas * 100, 1
                ) if total_piezas > 0 else 0.0
            }
        }
