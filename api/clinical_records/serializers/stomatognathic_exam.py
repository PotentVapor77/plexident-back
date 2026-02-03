# src/api/clinical_records/serializers/stomatognathic_exam.py
"""
Serializers para examen del sistema estomatognático
"""
from rest_framework import serializers
from django.utils.dateparse import parse_date

from api.patients.models.examen_estomatognatico import ExamenEstomatognatico
from api.patients.serializers import ExamenEstomatognaticoSerializer
from .base import BaseWritableNestedSerializer


class WritableExamenEstomatognaticoSerializer(
    BaseWritableNestedSerializer,
    ExamenEstomatognaticoSerializer
):
    """Serializer writable para examen estomatognático anidado"""
    
    class Meta(ExamenEstomatognaticoSerializer.Meta):
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
