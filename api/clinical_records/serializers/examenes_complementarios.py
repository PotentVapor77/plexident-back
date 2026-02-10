# api/clinical_records/serializers/examenes_complementarios.py
"""
Serializer para Exámenes Complementarios dentro del contexto de Historiales Clínicos.
Permite lectura y escritura desde los endpoints del historial.
"""
from rest_framework import serializers
from api.patients.models.examenes_complementarios import ExamenesComplementarios


class WritableExamenesComplementariosSerializer(serializers.ModelSerializer):
    """
    Serializer de escritura para exámenes complementarios
    vinculados al historial clínico.
    """
    
    # Campos de solo lectura informativos
    estado_examenes = serializers.CharField(read_only=True)
    resumen_examenes_complementarios = serializers.CharField(read_only=True)
    tiene_pedido_examenes_pendiente = serializers.BooleanField(read_only=True)
    tiene_informe_examenes_completado = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = ExamenesComplementarios
        fields = [
            'id',
            'paciente',
            # Pedido de exámenes
            'pedido_examenes',
            'pedido_examenes_detalle',
            # Informe de exámenes
            'informe_examenes',
            'informe_examenes_detalle',
            # Campos computados (read-only)
            'estado_examenes',
            'resumen_examenes_complementarios',
            'tiene_pedido_examenes_pendiente',
            'tiene_informe_examenes_completado',
            # Auditoría
            'fecha_creacion',
            'fecha_modificacion',
        ]
        read_only_fields = [
            'id',
            'fecha_creacion',
            'fecha_modificacion',
        ]


class ExamenesComplementariosResumenSerializer(serializers.ModelSerializer):
    """
    Serializer ligero para incluir en el detalle del historial clínico.
    """
    estado_examenes = serializers.CharField(read_only=True)
    resumen_examenes_complementarios = serializers.CharField(read_only=True)
    
    class Meta:
        model = ExamenesComplementarios
        fields = [
            'id',
            'pedido_examenes',
            'pedido_examenes_detalle',
            'informe_examenes',
            'informe_examenes_detalle',
            'estado_examenes',
            'resumen_examenes_complementarios',
            'fecha_creacion',
        ]
        read_only_fields = fields