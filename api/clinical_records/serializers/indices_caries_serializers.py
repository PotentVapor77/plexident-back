# api/patients/serializers/indices_caries_serializers.py
"""
Serializers para índices de caries (CPO/ceo)
"""

from rest_framework import serializers

from api.odontogram.models import IndiceCariesSnapshot



class IndicesCariesSerializer(serializers.ModelSerializer):
    """
    Serializer base (Read-only) para índices de caries
    """
    
    class Meta:
        model = IndiceCariesSnapshot  
        fields = '__all__'
        read_only_fields = ['id', 'fecha_creacion', 'fecha_modificacion']


class WritableIndicesCariesSerializer(serializers.ModelSerializer):
    """
    Serializer writable para anidación en historial clínico
    Hereda de BaseWritableNestedSerializer si existe, sino de ModelSerializer
    """
    
    class Meta:
        model = IndiceCariesSnapshot
        fields = '__all__'
        read_only_fields = ['id', 'fecha']
    
    def validate(self, data):
        """Validaciones personalizadas"""
        # Validar que al menos un índice tenga valor
        indices = [
            'cpo_c', 'cpo_p', 'cpo_o', 'cpo_total',
            'ceo_c', 'ceo_e', 'ceo_o', 'ceo_total'
        ]
        
        if not any(data.get(field) for field in indices if data.get(field) is not None):
            raise serializers.ValidationError(
                'Debe proporcionar al menos un valor de índice'
            )
        
        return data