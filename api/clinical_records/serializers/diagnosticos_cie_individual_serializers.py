# api/clinical_records/serializers/diagnosticos_cie_individual_serializers.py
from rest_framework import serializers
from api.clinical_records.models import DiagnosticoCIEHistorial

class DiagnosticoCIEIndividualSerializer(serializers.ModelSerializer):
    """Serializer para gestión individual de diagnósticos CIE"""
    
    diagnostico_nombre = serializers.CharField(source='nombre_diagnostico', read_only=True)
    codigo_cie = serializers.CharField(read_only=True)
    diente_fdi = serializers.CharField(read_only=True)
    superficie_nombre = serializers.CharField(read_only=True)
    tipo_cie_display = serializers.CharField(source='get_tipo_cie_display', read_only=True)
    
    class Meta:
        model = DiagnosticoCIEHistorial
        fields = [
            'id',
            'diagnostico_dental',
            'diagnostico_nombre',
            'codigo_cie',
            'diente_fdi',
            'superficie_nombre',
            'tipo_cie',
            'tipo_cie_display',
            'activo',
            'fecha_creacion',
            'fecha_modificacion',
            'creado_por',
            'actualizado_por',
        ]
        read_only_fields = [
            'id',
            'diagnostico_dental',
            'historial_clinico',
            'diagnostico_nombre',
            'codigo_cie',
            'diente_fdi',
            'superficie_nombre',
            'fecha_creacion',
            'fecha_modificacion',
            'creado_por',
            'actualizado_por',
        ]

class DiagnosticoCIEUpdateSerializer(serializers.Serializer):
    """Serializer para actualizar tipo CIE individual"""
    
    tipo_cie = serializers.ChoiceField(
        choices=DiagnosticoCIEHistorial.TipoCIE.choices,
        required=True
    )
    
    def validate(self, data):
        """Validación adicional"""
        if not self.instance:
            raise serializers.ValidationError("Instancia requerida para actualización")
        return data

class SincronizarDiagnosticosSerializer(serializers.Serializer):
    """Serializer para sincronización de diagnósticos"""
    
    diagnosticos_finales = serializers.ListField(
        child=serializers.DictField(),
        required=True,
        help_text="Lista de diagnósticos que deben permanecer en el historial"
    )
    
    tipo_carga = serializers.ChoiceField(
        choices=[
            ('nuevos', 'Solo nuevos diagnósticos'),
            ('todos', 'Todos los diagnósticos del snapshot'),
        ],
        required=True
    )
    
    def validate_diagnosticos_finales(self, value):
        """Validar estructura de diagnósticos finales"""
        for diag in value:
            if not diag.get('diagnostico_dental_id'):
                raise serializers.ValidationError(
                    "Cada diagnóstico debe tener 'diagnostico_dental_id'"
                )
            if not diag.get('tipo_cie'):
                raise serializers.ValidationError(
                    "Cada diagnóstico debe tener 'tipo_cie' (PRE/DEF)"
                )
        return value