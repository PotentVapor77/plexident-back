# src/api/clinical_records/serializers/medical_history.py
"""
Serializers para antecedentes patológicos personales y familiares
"""
from rest_framework import serializers
from api.patients.models.antecedentes_personales import AntecedentesPersonales
from api.patients.models.antecedentes_familiares import AntecedentesFamiliares
from api.patients.serializers import (
    AntecedentesPersonalesSerializer,
    AntecedentesFamiliaresSerializer,
)
from .base import BaseWritableNestedSerializer


class WritableAntecedentesPersonalesSerializer(
    BaseWritableNestedSerializer,
    AntecedentesPersonalesSerializer
):
    """Serializer writable para antecedentes personales anidados"""
    
    class Meta(AntecedentesPersonalesSerializer.Meta):
        read_only_fields = BaseWritableNestedSerializer.Meta.read_only_fields


class WritableAntecedentesFamiliaresSerializer(
    BaseWritableNestedSerializer,
    AntecedentesFamiliaresSerializer
):
    """Serializer writable para antecedentes familiares anidados"""
    
    class Meta(AntecedentesFamiliaresSerializer.Meta):
        read_only_fields = BaseWritableNestedSerializer.Meta.read_only_fields
