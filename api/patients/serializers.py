# api/patients/serializers.py
from rest_framework import serializers

from api.patients.models.paciente import Paciente
from api.patients.models.antecedentes_personales import AntecedentesPersonales
from api.patients.models.antecedentes_familiares import AntecedentesFamiliares
from api.patients.models.constantes_vitales import ConstantesVitales
from api.patients.models.examen_estomatognatico import ExamenEstomatognatico


class PacienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paciente
        fields = '__all__'
        read_only_fields = [
            'id', 'creado_por', 'actualizado_por',
            'fecha_creacion', 'fecha_modificacion'
        ]

    def to_representation(self, instance):
        """Formato compatible con frontend"""
        data = super().to_representation(instance)
        
        # Fechas a ISO string
        if data.get('fecha_nacimiento'):
            data['fecha_nacimiento'] = instance.fecha_nacimiento.isoformat()
        if data.get('fecha_creacion'):
            data['fecha_creacion'] = instance.fecha_creacion.isoformat()
        if data.get('fecha_modificacion') and instance.fecha_modificacion:
            data['fecha_modificacion'] = instance.fecha_modificacion.isoformat()
            
        return data

    def validate_telefono(self, value):
        if value and (len(value) < 10 or not value.isdigit()):
            raise serializers.ValidationError("El teléfono debe tener al menos 10 números.")
        return value

    def validate_contacto_emergencia_telefono(self, value):
        if value and (len(value) < 10 or not value.isdigit()):
            raise serializers.ValidationError("El teléfono de emergencia debe tener al menos 10 números.")
        return value

    def validate_edad(self, value):
        if value <= 0 or value > 150:
            raise serializers.ValidationError("La edad debe estar entre 1 y 150 años.")
        return value

    def validate(self, attrs):
        if not attrs.get('nombres') or not attrs.get('apellidos'):
            raise serializers.ValidationError("Los nombres y apellidos son obligatorios.")
        if not attrs.get('cedula_pasaporte'):
            raise serializers.ValidationError("La cédula/pasaporte es obligatorio.")
        if attrs.get('sexo') == 'M' and attrs.get('embarazada') == 'SI':
            raise serializers.ValidationError("Un paciente masculino no puede estar marcado como embarazado.")
        return attrs


class ConstantesVitalesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConstantesVitales
        fields = "__all__"
        read_only_fields = [
            "id", "creado_por", "actualizado_por",
            "fecha_creacion", "fecha_modificacion",
        ]

    def validate_temperatura(self, value):
        if value and (value < 35 or value > 42):
            raise serializers.ValidationError("La temperatura debe estar entre 35°C y 42°C.")
        return value

    def validate_presion_arterial_sistolica(self, value):
        if value and (value < 50 or value > 250):
            raise serializers.ValidationError("La presión sistólica debe estar entre 50 y 250 mmHg.")
        return value

    def validate_presion_arterial_diastolica(self, value):
        if value and (value < 30 or value > 150):
            raise serializers.ValidationError("La presión diastólica debe estar entre 30 y 150 mmHg.")
        return value


class AntecedentesPersonalesSerializer(serializers.ModelSerializer):
    class Meta:
        model = AntecedentesPersonales
        fields = "__all__"
        read_only_fields = ["id", "creado_por", "actualizado_por", "fecha_creacion", "fecha_modificacion"]


class AntecedentesFamiliaresSerializer(serializers.ModelSerializer):
    class Meta:
        model = AntecedentesFamiliares
        fields = "__all__"
        read_only_fields = ["id", "creado_por", "actualizado_por", "fecha_creacion", "fecha_modificacion"]


class ExamenEstomatognaticoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamenEstomatognatico
        fields = "__all__"
        read_only_fields = ["id", "creado_por", "actualizado_por", "fecha_creacion", "fecha_modificacion"]
