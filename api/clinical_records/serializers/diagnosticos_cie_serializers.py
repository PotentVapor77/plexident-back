# api/clinical_records/serializers/diagnosticos_cie_serializers.py
from rest_framework import serializers
from api.odontogram.models import DiagnosticoDental
from api.odontogram.serializers.diagnostico_cie_serializer import DiagnosticoCIESerializer

class WritableDiagnosticoCIEHistorialSerializer(serializers.Serializer):
    """Serializer flexible para guardar múltiples diagnósticos CIE"""
    
    # Hacer los campos opcionales para lectura
    diagnosticos = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        allow_empty=True,
        help_text="Para escritura: lista de diagnósticos con IDs"
    )
    
    diagnosticos_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
        help_text="Alternativa: lista simple de IDs"
    )
    
    tipo_carga = serializers.ChoiceField(
        choices=[
            ('nuevos', 'Solo nuevos diagnósticos'),
            ('todos', 'Todos los diagnósticos del snapshot'),
        ],
        required=True
    )
    
    def validate(self, data):
        """Validar que se proporcione al menos un formato de diagnósticos"""
        if not data.get('diagnosticos') and not data.get('diagnosticos_ids'):
            raise serializers.ValidationError(
                'Debe proporcionar "diagnosticos" o "diagnosticos_ids"'
            )
        return data
    
    def to_representation(self, instance):
        """Para serialización de salida"""
        # Si instance es un dict (de create/update), devolverlo tal cual
        if isinstance(instance, dict):
            return instance
        
        # Si instance es un modelo, extraer sus diagnósticos
        try:
            # Aquí asumimos que el modelo tiene una relación 'diagnosticos'
            diagnosticos = instance.diagnosticos.all() if hasattr(instance, 'diagnosticos') else []
            diagnosticos_serializer = DiagnosticoCIESerializer(diagnosticos, many=True)
            
            return {
                'diagnosticos': diagnosticos_serializer.data,
                'tipo_carga': getattr(instance, 'tipo_carga_diagnosticos', 'todos'),
                'diagnosticos_ids': [str(d.id) for d in diagnosticos]
            }
        except AttributeError:
            # Si no se puede serializar, devolver estructura vacía
            return {
                'diagnosticos': [],
                'tipo_carga': 'todos',
                'diagnosticos_ids': []
            }
    
    def create(self, validated_data):
        """Crear registro de diagnósticos CIE"""
        # Lógica de creación (como la que ya tienes)
        historial_clinico = self.context.get('historial_clinico')
        creado_por = self.context.get('request').user if self.context.get('request') else None
        tipo_carga = validated_data['tipo_carga']
        
        # Manejar ambos formatos de entrada
        diagnosticos_ids = []
        
        if validated_data.get('diagnosticos_ids'):
            diagnosticos_ids = validated_data['diagnosticos_ids']
        elif validated_data.get('diagnosticos'):
            # Extraer IDs del formato complejo
            diagnosticos_ids = [
                diag.get('diagnostico_dental_id') or diag.get('diagnostico_dental', {}).get('id')
                for diag in validated_data['diagnosticos']
                if diag
            ]
            # Filtrar valores None
            diagnosticos_ids = [did for did in diagnosticos_ids if did]
        
        # Obtener diagnósticos
        diagnosticos = DiagnosticoDental.objects.filter(
            id__in=diagnosticos_ids,
            activo=True
        ).select_related(
            'diagnostico_catalogo',
            'superficie',
            'superficie__diente',
            'superficie__diente__paciente',
            'odontologo'
        )
        
        # Serializar para respuesta
        serializer = DiagnosticoCIESerializer(diagnosticos, many=True)
        
        return {
            'diagnosticos': serializer.data,
            'tipo_carga': tipo_carga,
            'diagnosticos_ids': diagnosticos_ids,
            'total': diagnosticos.count()
        }