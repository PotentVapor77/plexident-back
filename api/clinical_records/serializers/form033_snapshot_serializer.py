# api/clinical_records/serializers/form033_snapshot_serializer.py
"""
Serializers para Form033Snapshot
"""
from rest_framework import serializers
from api.clinical_records.models import Form033Snapshot


class Form033SnapshotSerializer(serializers.ModelSerializer):
    """
    Serializer completo para Form033Snapshot
    """
    capturado_por_nombre = serializers.CharField(
        source='capturado_por.get_full_name',
        read_only=True
    )
    
    resumen_estadistico = serializers.ReadOnlyField()
    
    historial_numero = serializers.CharField(
        source='historial_clinico.numero_historia_clinica_unica',
        read_only=True
    )
    
    class Meta:
        model = Form033Snapshot
        fields = [
            'id',
            'historial_clinico',
            'historial_numero',
            'datos_form033',
            'fecha_captura',
            'capturado_por',
            'capturado_por_nombre',
            'total_dientes_permanentes',
            'total_dientes_temporales',
            'total_caries',
            'total_ausentes',
            'total_obturados',
            'observaciones',
            'resumen_estadistico',
            'activo',
            'fecha_creacion',
        ]
        read_only_fields = [
            'id',
            'fecha_captura',
            'total_dientes_permanentes',
            'total_dientes_temporales',
            'total_caries',
            'total_ausentes',
            'total_obturados',
            'fecha_creacion',
        ]


class Form033SnapshotCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para crear Form033Snapshot
    """
    
    class Meta:
        model = Form033Snapshot
        fields = [
            'historial_clinico',
            'datos_form033',
            'capturado_por',
            'observaciones',
        ]
    
    def validate_datos_form033(self, value):
        """Validar que los datos tengan la estructura correcta"""
        if not isinstance(value, dict):
            raise serializers.ValidationError(
                'Los datos del Form033 deben ser un diccionario'
            )
        
        # Validar estructura básica
        required_keys = ['odontograma_permanente', 'odontograma_temporal']
        for key in required_keys:
            if key not in value:
                raise serializers.ValidationError(
                    f'Falta la clave requerida: {key}'
                )
        
        return value


class Form033SnapshotResumenSerializer(serializers.ModelSerializer):
    """
    Serializer ligero para listar snapshots (sin datos JSON completos)
    """
    capturado_por_nombre = serializers.CharField(
        source='capturado_por.get_full_name',
        read_only=True
    )
    
    resumen_estadistico = serializers.ReadOnlyField()
    
    class Meta:
        model = Form033Snapshot
        fields = [
            'id',
            'historial_clinico',
            'fecha_captura',
            'capturado_por_nombre',
            'total_dientes_permanentes',
            'total_dientes_temporales',
            'total_caries',
            'total_ausentes',
            'total_obturados',
            'resumen_estadistico',
        ]
