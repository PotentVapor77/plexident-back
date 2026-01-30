# api/clinical_records/serializers/oral_health_indicators.py
"""
Serializers para indicadores de salud bucal dentro del historial clínico
"""
from rest_framework import serializers
from api.odontogram.models import IndicadoresSaludBucal
from api.odontogram.constants import (
    ESCALA_PLACA, 
    ESCALA_CALCULO, 
    ESCALA_GINGIVITIS,
    NIVELES_FLUOROSIS,
    NIVELES_PERIODONTAL,
    TIPOS_OCLUSION
)


class OralHealthIndicatorsSerializer(serializers.ModelSerializer):
    paciente_nombre = serializers.SerializerMethodField()
    creado_por_nombre = serializers.SerializerMethodField()
    fecha_formateada = serializers.SerializerMethodField()
    valores_por_pieza = serializers.SerializerMethodField()
    informacion_calculo_json = serializers.SerializerMethodField()
    
    # Textos descriptivos (calculados)
    enfermedad_periodontal_display = serializers.SerializerMethodField()
    tipo_oclusion_display = serializers.SerializerMethodField()
    nivel_fluorosis_display = serializers.SerializerMethodField()
    nivel_gingivitis_display = serializers.SerializerMethodField()
    
    # Resúmenes (los que te daban error)
    resumen_higiene = serializers.SerializerMethodField()
    resumen_gingival = serializers.SerializerMethodField()
    informacion_calculo_json = serializers.SerializerMethodField()
    
    class Meta:
        model = IndicadoresSaludBucal
        fields = [
            'id', 'fecha', 'fecha_formateada', 'paciente_nombre', 'creado_por_nombre',
            'enfermedad_periodontal', 'enfermedad_periodontal_display',
            'tipo_oclusion', 'tipo_oclusion_display',
            'nivel_fluorosis', 'nivel_fluorosis_display',
            'gi_promedio_gingivitis', 'nivel_gingivitis_display',
            'observaciones', 'informacion_calculo_json',
            'valores_por_pieza', 'ohi_promedio_placa', 'ohi_promedio_calculo',
            'gi_promedio_gingivitis', 'resumen_higiene', 'resumen_gingival', 'informacion_calculo_json','activo',
        ]
        read_only_fields = fields  
    
    def get_paciente_nombre(self, obj):
        """Nombre completo del paciente"""
        if obj.paciente:
            return f"{obj.paciente.nombres} {obj.paciente.apellidos}"
        return None
    
    def get_creado_por_nombre(self, obj):
        """Nombre del odontólogo que creó los indicadores"""
        if obj.creado_por:
            return f"{obj.creado_por.nombres} {obj.creado_por.apellidos}"
        return "N/A"
    
    def get_fecha_formateada(self, obj):
        """Fecha formateada para mostrar"""
        if obj.fecha:
            return obj.fecha.strftime("%d/%m/%Y %H:%M")
        return None
    
    def get_enfermedad_periodontal_display(self, obj):
        """Descripción de enfermedad periodontal"""
        if obj.enfermedad_periodontal:
            return NIVELES_PERIODONTAL.get(obj.enfermedad_periodontal, obj.enfermedad_periodontal)
        return None
    
    def get_tipo_oclusion_display(self, obj):
        """Descripción de tipo de oclusión"""
        if obj.tipo_oclusion:
            return TIPOS_OCLUSION.get(obj.tipo_oclusion, obj.tipo_oclusion)
        return None
    
    def get_nivel_fluorosis_display(self, obj):
        """Descripción de nivel de fluorosis"""
        if obj.nivel_fluorosis:
            return NIVELES_FLUOROSIS.get(obj.nivel_fluorosis, obj.nivel_fluorosis)
        return None
    
    def get_nivel_gingivitis_display(self, obj):
        """Descripción de nivel de gingivitis"""
        return obj.get_nivel_gingivitis_display() if obj.gi_promedio_gingivitis else "N/A"
    
    def get_valores_por_pieza(self, obj):
        """Organiza valores por pieza dental con descripciones"""
        piezas = ['16', '11', '26', '36', '31', '46']
        resultado = []
        
        for pieza in piezas:
            placa = getattr(obj, f'pieza_{pieza}_placa', None)
            calculo = getattr(obj, f'pieza_{pieza}_calculo', None)
            gingivitis = getattr(obj, f'pieza_{pieza}_gingivitis', None)
            
            # Obtener descripciones de escalas
            placa_desc = ESCALA_PLACA.get(placa) if placa is not None else None
            calculo_desc = ESCALA_CALCULO.get(calculo) if calculo is not None else None
            gingivitis_desc = ESCALA_GINGIVITIS.get(gingivitis) if gingivitis is not None else None
            
            resultado.append({
                'pieza': pieza,
                'placa': {
                    'valor': placa,
                    'descripcion': placa_desc,
                    'escala': 'Índice de Placa de Silness & Löe (0-3)'
                },
                'calculo': {
                    'valor': calculo,
                    'descripcion': calculo_desc,
                    'escala': 'Índice de Cálculo de Greene & Vermillion (0-3)'
                },
                'gingivitis': {
                    'valor': gingivitis,
                    'descripcion': gingivitis_desc,
                    'escala': 'Índice Gingival de Löe & Silness (0-3)'
                },
                'completo': all(v is not None for v in [placa, calculo, gingivitis])
            })
        
        return resultado
    
    def get_resumen_higiene(self, obj):
        """Resumen de higiene oral basado en OHI-S"""
        if obj.ohi_promedio_placa is not None and obj.ohi_promedio_calculo is not None:
            total_ohi = obj.ohi_promedio_placa + obj.ohi_promedio_calculo
            
            if total_ohi <= 0.6:
                return {
                    'nivel': 'Excelente',
                    'valor': total_ohi,
                    'rango': '0 - 0.6',
                    'recomendacion': 'Mantener excelentes hábitos de higiene oral'
                }
            elif total_ohi <= 1.2:
                return {
                    'nivel': 'Bueno',
                    'valor': total_ohi,
                    'rango': '0.7 - 1.2',
                    'recomendacion': 'Continuar con buena higiene, mejorar técnica de cepillado'
                }
            elif total_ohi <= 1.8:
                return {
                    'nivel': 'Regular',
                    'valor': total_ohi,
                    'rango': '1.3 - 1.8',
                    'recomendacion': 'Mejorar frecuencia y técnica de cepillado, considerar uso de hilo dental'
                }
            elif total_ohi <= 3.0:
                return {
                    'nivel': 'Deficiente',
                    'valor': total_ohi,
                    'rango': '1.9 - 3.0',
                    'recomendacion': 'Instrucción detallada de higiene oral, evaluación de técnica'
                }
            else:
                return {
                    'nivel': 'Pésimo',
                    'valor': total_ohi,
                    'rango': '> 3.0',
                    'recomendacion': 'Urgente: educación en higiene oral y posible tratamiento profesional'
                }
        
        return {
            'nivel': 'Sin datos',
            'valor': None,
            'rango': None,
            'recomendacion': 'Completar evaluación de indicadores'
        }
    
    def get_resumen_gingival(self, obj):
        """Resumen de salud gingival basado en GI"""
        if obj.gi_promedio_gingivitis is not None:
            if obj.gi_promedio_gingivitis <= 0.1:
                return {
                    'nivel': 'Normal',
                    'valor': obj.gi_promedio_gingivitis,
                    'rango': '0 - 0.1',
                    'recomendacion': 'Encías saludables, mantener hábitos actuales'
                }
            elif obj.gi_promedio_gingivitis <= 1.0:
                return {
                    'nivel': 'Leve',
                    'valor': obj.gi_promedio_gingivitis,
                    'rango': '0.2 - 1.0',
                    'recomendacion': 'Mejorar higiene oral, evaluar técnica de cepillado'
                }
            elif obj.gi_promedio_gingivitis <= 2.0:
                return {
                    'nivel': 'Moderada',
                    'valor': obj.gi_promedio_gingivitis,
                    'rango': '1.1 - 2.0',
                    'recomendacion': 'Evaluación periodontal, posible tratamiento profesional'
                }
            else:
                return {
                    'nivel': 'Severa',
                    'valor': obj.gi_promedio_gingivitis,
                    'rango': '> 2.0',
                    'recomendacion': 'Urgente: evaluación y tratamiento periodontal profesional'
                }
        
        return {
            'nivel': 'Sin datos',
            'valor': None,
            'rango': None,
            'recomendacion': 'Completar evaluación gingival'
        }
        
    
    def get_informacion_calculo_json(self, obj):
        """Información de cálculo estructurada"""
        if obj.informacion_calculo:
            return obj.informacion_calculo
        return None
    def get_nivel_gingivitis_display(self, obj):
        """
        Traducción manual de valor numérico a etiqueta de texto
        basada en los rangos de salud bucal.
        """
        valor = obj.gi_promedio_gingivitis
        
        if valor is None:
            return "N/A"
        
        # Lógica basada en la escala de Loe y Silness (común en odontología)
        if valor == 0:
            return "Sano"
        elif 0.1 <= valor <= 1.0:
            return "Gingivitis Leve"
        elif 1.1 <= valor <= 2.0:
            return "Gingivitis Moderada"
        elif 2.1 <= valor <= 3.0:
            return "Gingivitis Severa"
            
        return "N/A"

class OralHealthIndicatorsRefreshSerializer(serializers.Serializer):
    """
    Serializer para la operación de refresh de indicadores
    """
    paciente_id = serializers.UUIDField(required=True)
    incluir_historial = serializers.BooleanField(default=False, required=False)