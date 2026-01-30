# api/odontogram/indicadores/calculos_service.py
"""
Servicio para calcular indicadores de salud bucal
"""

from typing import Dict, List, Optional, Tuple

from api.odontogram.constants import ESCALA_CALCULO, ESCALA_GINGIVITIS, ESCALA_PLACA, calcular_gi_promedio, calcular_ohi_s


class CalculosIndicadoresService:
    """
    Servicio para realizar cálculos de indicadores de salud bucal
    """
    
    @staticmethod
    def calcular_ohi_completo(
        valores_placa: Dict[str, int],
        valores_calculo: Dict[str, int]
    ) -> Dict:
        """
        Calcula el OHI-S completo con interpretación por pieza
        """
        # Filtrar valores nulos
        placa_vals = [v for v in valores_placa.values() if v is not None]
        calculo_vals = [v for v in valores_calculo.values() if v is not None]
        
        if not placa_vals or not calculo_vals:
            return {
                'indice_placa': None,
                'indice_calculo': None,
                'ohi_s': None,
                'interpretacion': 'Datos incompletos',
                'por_pieza': []
            }
        
        # Calcular totales
        total_placa = sum(placa_vals)
        total_calculo = sum(calculo_vals)
        num_superficies = len(placa_vals)
        
        # Calcular OHI-S
        ohi_s_result = calcular_ohi_s(total_placa, total_calculo, num_superficies)
        
        # Crear detalle por pieza
        detalle_piezas = []
        for pieza in valores_placa.keys():
            placa = valores_placa.get(pieza)
            calculo = valores_calculo.get(pieza)
            
            if placa is not None and calculo is not None:
                detalle_piezas.append({
                    'pieza': pieza,
                    'placa': placa,
                    'calculo': calculo,
                    'placa_descripcion': ESCALA_PLACA.get(placa, 'Desconocido'),
                    'calculo_descripcion': ESCALA_CALCULO.get(calculo, 'Desconocido'),
                    'subtotal': placa + calculo
                })
        
        return {
            **ohi_s_result,
            'detalle_piezas': detalle_piezas,
            'totales': {
                'placa': total_placa,
                'calculo': total_calculo,
                'superficies_evaluadas': num_superficies
            }
        }
    
    @staticmethod
    def calcular_gingivitis_completo(
        valores_gingivitis: Dict[str, int]
    ) -> Dict:
        """
        Calcula el Índice Gingival completo
        """
        # Filtrar valores nulos
        gingivitis_vals = [v for v in valores_gingivitis.values() if v is not None]
        
        if not gingivitis_vals:
            return {
                'promedio': None,
                'interpretacion': 'Datos incompletos',
                'por_pieza': []
            }
        
        # Calcular total
        total_gingivitis = sum(gingivitis_vals)
        num_superficies = len(gingivitis_vals)
        
        # Calcular GI promedio
        gi_result = calcular_gi_promedio(total_gingivitis, num_superficies)
        
        # Crear detalle por pieza
        detalle_piezas = []
        for pieza, valor in valores_gingivitis.items():
            if valor is not None:
                detalle_piezas.append({
                    'pieza': pieza,
                    'valor': valor,
                    'descripcion': ESCALA_GINGIVITIS.get(valor, 'Desconocido')
                })
        
        return {
            **gi_result,
            'detalle_piezas': detalle_piezas,
            'totales': {
                'gingivitis': total_gingivitis,
                'superficies_evaluadas': num_superficies
            }
        }
    
    @staticmethod
    def calcular_resumen_completo(
        valores_placa: Dict[str, int],
        valores_calculo: Dict[str, int],
        valores_gingivitis: Dict[str, int]
    ) -> Dict:
        """
        Calcula un resumen completo de todos los indicadores
        """
        ohi_s_result = CalculosIndicadoresService.calcular_ohi_completo(valores_placa, valores_calculo)
        gi_result = CalculosIndicadoresService.calcular_gingivitis_completo(valores_gingivitis)
        
        # Determinar recomendaciones basadas en los resultados
        recomendaciones = CalculosIndicadoresService.generar_recomendaciones(ohi_s_result, gi_result)
        
        return {
            'ohi_s': ohi_s_result,
            'indice_gingival': gi_result,
            'recomendaciones': recomendaciones,
            'resumen': {
                'higiene_oral': ohi_s_result.get('interpretacion', 'Sin datos'),
                'salud_gingival': gi_result.get('interpretacion', 'Sin datos'),
                'riesgo_periodontal': CalculosIndicadoresService.determinar_riesgo_periodontal(
                    ohi_s_result.get('ohi_s'), 
                    gi_result.get('promedio')
                )
            }
        }
    
    @staticmethod
    def generar_recomendaciones(ohi_s_result: Dict, gi_result: Dict) -> List[str]:
        """
        Genera recomendaciones personalizadas basadas en los resultados
        """
        recomendaciones = []
        
        # Recomendaciones basadas en OHI-S
        ohi_s_valor = ohi_s_result.get('ohi_s')
        if ohi_s_valor is not None:
            if ohi_s_valor > 1.8:
                recomendaciones.append("Higiene oral deficiente. Se recomienda mejorar técnica de cepillado")
                recomendaciones.append("Considerar uso de hilo dental y enjuague bucal diario")
                recomendaciones.append("Evaluar necesidad de profilaxis profesional")
            elif ohi_s_valor > 1.2:
                recomendaciones.append("Higiene oral regular. Refinar técnica de cepillado")
                recomendaciones.append("Asegurar cepillado mínimo 2 veces al día")
        
        # Recomendaciones basadas en Índice Gingival
        gi_promedio = gi_result.get('promedio')
        if gi_promedio is not None:
            if gi_promedio > 1.0:
                recomendaciones.append("Presencia de gingivitis. Evaluar necesidad de terapia periodontal")
                recomendaciones.append("Mejorar higiene en áreas con inflamación")
            elif gi_promedio > 0.1:
                recomendaciones.append("Gingivitis leve. Mantener buena higiene oral")
        
        # Recomendaciones generales si no hay específicas
        if not recomendaciones:
            recomendaciones.append("Mantener buena higiene oral actual")
            recomendaciones.append("Continuar con revisiones periódicas")
        
        return recomendaciones
    
    @staticmethod
    def determinar_riesgo_periodontal(ohi_s: Optional[float], gi_promedio: Optional[float]) -> str:
        """
        Determina el riesgo periodontal basado en OHI-S y GI
        """
        if ohi_s is None or gi_promedio is None:
            return "Riesgo indeterminado (datos incompletos)"
        
        if ohi_s > 2.0 and gi_promedio > 1.5:
            return "Alto riesgo"
        elif ohi_s > 1.2 or gi_promedio > 0.5:
            return "Riesgo moderado"
        else:
            return "Bajo riesgo"