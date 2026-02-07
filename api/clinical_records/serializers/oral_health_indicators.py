# api/clinical_records/serializers/oral_health_indicators.py
"""
Serializer para Indicadores de Salud Bucal con mapeo correcto de piezas suplentes
"""
from rest_framework import serializers
from api.odontogram.models import IndicadoresSaludBucal


class OralHealthIndicatorsSerializer(serializers.ModelSerializer):
    """
    Serializer para Indicadores de Salud Bucal
    
    FUNCIÓN CRÍTICA: Mapea correctamente los valores almacenados en campos de piezas
    principales (16, 11, 26, 36, 31, 46) a las piezas realmente usadas (ej: 21 como suplente de 11).
    
    Ejemplo:
        BD almacena: pieza_11_placa = 1.2
        piezas_mapeo dice: pieza 11 usa código 21 como suplente
        Serializer retorna: {pieza_usada: "21", placa: {valor: 1.2}}
    """
    
    # Campos calculados
    enfermedad_periodontal_display = serializers.SerializerMethodField()
    tipo_oclusion_display = serializers.SerializerMethodField()
    nivel_fluorosis_display = serializers.SerializerMethodField()
    nivel_gingivitis_display = serializers.SerializerMethodField()
    valores_por_pieza = serializers.SerializerMethodField()
    informacion_piezas = serializers.SerializerMethodField()
    
    class Meta:
        model = IndicadoresSaludBucal
        fields = [
            'id',
            'paciente',
            'fecha',
            'fecha_modificacion',
            
            # Promedios
            'ohi_promedio_placa',
            'ohi_promedio_calculo',
            'gi_promedio_gingivitis',
            
            # Diagnósticos
            'enfermedad_periodontal',
            'enfermedad_periodontal_display',
            'tipo_oclusion',
            'tipo_oclusion_display',
            'nivel_fluorosis',
            'nivel_fluorosis_display',
            'nivel_gingivitis_display',
            
            # Información estructurada
            'valores_por_pieza',
            'informacion_piezas',
            'piezas_usadas_en_registro',
            
            # Metadata
            'observaciones',
            'activo',
        ]
        read_only_fields = ['id', 'fecha', 'fecha_modificacion']
    
    def get_enfermedad_periodontal_display(self, obj):
        """Retorna la descripción legible de la enfermedad periodontal"""
        return obj.get_enfermedad_periodontal_display() if obj.enfermedad_periodontal else None
    
    def get_tipo_oclusion_display(self, obj):
        """Retorna la descripción legible del tipo de oclusión"""
        return obj.get_tipo_oclusion_display() if obj.tipo_oclusion else None
    
    def get_nivel_fluorosis_display(self, obj):
        """Retorna la descripción legible del nivel de fluorosis"""
        return obj.get_nivel_fluorosis_display() if obj.nivel_fluorosis else None
    
    def get_nivel_gingivitis_display(self, obj):
        """
        Determina el nivel de gingivitis basado en el promedio
        Escala: 0 = Ninguna, 0-0.3 = Leve, 0.3-0.6 = Moderada, >0.6 = Severa
        """
        gi = obj.gi_promedio_gingivitis
        if gi is None:
            return None
        elif gi == 0:
            return "No presenta"
        elif 0 < gi <= 0.3:
            return "Leve"
        elif 0.3 < gi <= 0.6:
            return "Moderada"
        else:
            return "Severa"
    
    def get_valores_por_pieza(self, obj):
        """
        ⚡ FUNCIÓN CRÍTICA: Mapea correctamente los valores almacenados
        
        El modelo tiene campos FIJOS: pieza_16_placa, pieza_11_placa, etc.
        Cuando se usa una pieza suplente (ej: 21 en lugar de 11):
        - Los valores están en pieza_11_placa (almacenamiento)
        - Pero debemos retornar pieza_usada: "21" (presentación)
        
        Esta función hace ese mapeo leyendo de los campos originales
        pero presentando con el código usado real.
        """
        valores = []
        
        # Obtener el mapeo de piezas del registro
        piezas_mapeo = obj.piezas_usadas_en_registro.get('piezas_mapeo', {})
        
        # Las 6 piezas principales del sistema (campos fijos del modelo)
        piezas_principales = ['16', '11', '26', '36', '31', '46']
        
        for pieza_original in piezas_principales:
            # 1. Obtener información del mapeo
            pieza_info = piezas_mapeo.get(pieza_original, {})
            codigo_usado = pieza_info.get('codigo_usado', pieza_original)
            es_alternativa = pieza_info.get('es_alternativa', False)
            disponible = pieza_info.get('disponible', True)
            
            # 2. LEER VALORES del campo de la pieza ORIGINAL
            # Esto es CRÍTICO: aunque usemos la pieza 21, los valores
            # están guardados en pieza_11_placa (porque son los únicos campos que existen)
            placa = getattr(obj, f'pieza_{pieza_original}_placa', None)
            calculo = getattr(obj, f'pieza_{pieza_original}_calculo', None)
            gingivitis = getattr(obj, f'pieza_{pieza_original}_gingivitis', None)
            
            # 3. Crear objeto con la pieza USADA
            # Aquí es donde hacemos el mapeo: presentamos como si fuera la pieza 21
            # aunque los datos vienen de pieza_11_*
            valores.append({
                'pieza_original': pieza_original,
                'pieza_usada': codigo_usado,  # ← Aquí está el mapeo
                'es_alternativa': es_alternativa,
                'disponible': disponible,
                'placa': {
                    'valor': placa,
                    'descripcion': self._get_descripcion_valor(placa, 'placa'),
                    'escala': '0-3'
                },
                'calculo': {
                    'valor': calculo,
                    'descripcion': self._get_descripcion_valor(calculo, 'calculo'),
                    'escala': '0-3'
                },
                'gingivitis': {
                    'valor': gingivitis,
                    'descripcion': self._get_descripcion_gingivitis(gingivitis),
                    'escala': '0-1'
                },
                'completo': all(v is not None for v in [placa, calculo, gingivitis]),
                'mensaje_alternativa': pieza_info.get('motivo') if es_alternativa else None
            })
        
        return valores
    
    def get_informacion_piezas(self, obj):
        """
        Retorna información estructurada sobre las piezas usadas en el registro
        
        Incluye:
        - Dentición (permanente/temporal)
        - Estadísticas (total, originales, alternativas)
        - Mapeo completo de piezas
        - Mensajes y advertencias
        """
        piezas_registro = obj.piezas_usadas_en_registro or {}
        piezas_mapeo = piezas_registro.get('piezas_mapeo', {})
        estadisticas = piezas_registro.get('estadisticas', {})
        
        # Generar mensaje descriptivo
        total_piezas = estadisticas.get('total_piezas', 0)
        piezas_originales = estadisticas.get('piezas_originales', 0)
        piezas_alternativas = estadisticas.get('piezas_alternativas', 0)
        
        mensaje = f"Registro realizado con {total_piezas} piezas"
        if piezas_alternativas > 0:
            mensaje += f" ({piezas_originales} originales, {piezas_alternativas} suplentes)"
        
        # Generar advertencias para piezas suplentes
        advertencias = []
        for pieza_original, info in piezas_mapeo.items():
            if info.get('es_alternativa', False):
                advertencias.append(
                    f"Pieza {info.get('codigo_usado')} usada como suplente de {pieza_original}"
                )
        
        return {
            'tiene_metadata': bool(piezas_mapeo),
            'denticion': piezas_registro.get('denticion', 'permanente'),
            'estadisticas': estadisticas,
            'piezas_mapeo': piezas_mapeo,  # ← Frontend usa esto para badges
            'mensaje': mensaje,
            'advertencia': '; '.join(advertencias) if advertencias else None
        }
    
    def _get_descripcion_valor(self, valor, tipo):
        """
        Obtiene descripción legible para valores de placa/cálculo
        
        Escala 0-3:
        0 = Ausente
        1 = Leve
        2 = Moderado
        3 = Severo
        """
        if valor is None:
            return None
        
        if tipo in ['placa', 'calculo']:
            descripciones = {
                0: "Ausente",
                1: "Leve",
                2: "Moderado",
                3: "Severo"
            }
            return descripciones.get(valor, "Desconocido")
        return None
    
    def _get_descripcion_gingivitis(self, valor):
        """
        Obtiene descripción legible para gingivitis
        
        Escala 0-1:
        0 = Sin sangrado
        1 = Con sangrado
        """
        if valor is None:
            return None
        
        if valor == 0:
            return "Sin sangrado"
        elif valor == 1:
            return "Con sangrado"
        return "Desconocido"


class OralHealthIndicatorsRefreshSerializer(serializers.Serializer):
    """
    Serializer para la respuesta del endpoint de recarga de indicadores
    
    Usado en: GET /api/clinical-records/indicadores-salud-bucal/{paciente_id}/recargar/
    """
    valores = serializers.DictField(
        help_text="Valores prellenados de las piezas"
    )
    metadata_registro = serializers.DictField(
        help_text="Metadata del registro anterior"
    )
    estado_actual_piezas = serializers.DictField(
        help_text="Estado actual de las piezas del paciente"
    )
    advertencias = serializers.ListField(
        help_text="Advertencias sobre cambios en disponibilidad de piezas"
    )