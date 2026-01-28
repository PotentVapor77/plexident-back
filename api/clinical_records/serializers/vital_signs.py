# src/api/clinical_records/serializers/vital_signs.py
"""
Serializers para constantes vitales
"""
from rest_framework import serializers
from django.utils.dateparse import parse_date
import datetime

from api.patients.models.constantes_vitales import ConstantesVitales
from api.patients.serializers import ConstantesVitalesSerializer
from .base import BaseWritableNestedSerializer


class WritableConstantesVitalesSerializer(
    BaseWritableNestedSerializer,
    ConstantesVitalesSerializer
):
    """Serializer writable para constantes vitales anidadas"""
    
    fecha_consulta = serializers.DateField(
        required=False, 
        format='%Y-%m-%d', 
        input_formats=['%Y-%m-%d', 'iso-8601']
    )
    
    class Meta(ConstantesVitalesSerializer.Meta):
        read_only_fields = BaseWritableNestedSerializer.Meta.read_only_fields
    
    def to_internal_value(self, data):
        """Manejar fecha_consulta como string date"""
        if 'fecha_consulta' in data and isinstance(data['fecha_consulta'], str):
            try:
                parsed_date = parse_date(data['fecha_consulta'])
                if parsed_date:
                    data['fecha_consulta'] = parsed_date
            except (ValueError, TypeError):
                pass
        return super().to_internal_value(data)
    
    def to_representation(self, instance):
        """Forzar conversión de datetime a date"""
        if hasattr(instance, 'fecha_consulta') and isinstance(
            instance.fecha_consulta, datetime.datetime
        ):
            instance.fecha_consulta = instance.fecha_consulta.date()
        return super().to_representation(instance)


class VitalSignsFieldsMixin:
    """Mixin para campos individuales de constantes vitales (write-only)"""
    
    temperatura = serializers.DecimalField(
        max_digits=4,
        decimal_places=1,
        required=False,
        allow_null=True,
        write_only=True,
    )
    pulso = serializers.IntegerField(
        required=False, 
        allow_null=True, 
        write_only=True
    )
    frecuencia_respiratoria = serializers.IntegerField(
        required=False, 
        allow_null=True, 
        write_only=True
    )
    presion_arterial = serializers.CharField(
        required=False, 
        allow_blank=True, 
        write_only=True
    )
    motivo_consulta_texto = serializers.CharField(
        required=False,
        allow_blank=True,
        write_only=True,
        help_text='Motivo de consulta para nueva constante vital',
    )
    enfermedad_actual_texto = serializers.CharField(
        required=False,
        allow_blank=True,
        write_only=True,
        help_text='Enfermedad actual para nueva constante vital',
    )
