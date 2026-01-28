# src/api/clinical_records/serializers/base.py

"""
Serializers base y utilidades compartidas
"""
import datetime
from rest_framework import serializers


class SafeDateField(serializers.DateField):
    """Campo DateField seguro que maneja datetime"""
    
    def to_representation(self, value):
        if isinstance(value, datetime.datetime):
            return value.date().isoformat()
        return super().to_representation(value)


class BaseWritableNestedSerializer(serializers.ModelSerializer):
    """Clase base para todos los serializers anidados escribibles"""
    
    id = serializers.UUIDField(required=False)
    
    class Meta:
        abstract = True
        read_only_fields = (
            'fecha_creacion',
            'fecha_modificacion',
            'creado_por',
            'actualizado_por',
        )


class DateFormatterMixin:
    """Mixin para formatear campos de fecha en to_representation"""
    
    def format_dates(self, data, instance, date_fields):
        """Formatea múltiples campos de fecha"""
        for field in date_fields:
            if data.get(field):
                value = getattr(instance, field, None)
                if value:
                    data[field] = value.isoformat()
        return data
