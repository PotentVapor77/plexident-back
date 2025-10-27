from rest_framework import serializers
from .models import Paciente

class PacienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paciente
        fields = '__all__'
        read_only_fields = ['created_by', 'updated_by', 'created_at', 'updated_at']

    def validate_telefono(self, value):
        if len(value) < 10 or not value.isdigit():
            raise serializers.ValidationError("El teléfono debe tener al menos 10 números.")
        return value

    def validate_contacto_emergencia_telefono(self, value):
        if value and (len(value) < 10 or not value.isdigit()):
            raise serializers.ValidationError("El teléfono de emergencia debe tener al menos 10 números.")
        return value

    def validate(self, attrs):
        if not attrs.get('nombres'):
            raise serializers.ValidationError("El nombre es obligatorio.")
        if not attrs.get('apellidos'):
            raise serializers.ValidationError("El apellido es obligatorio.")
        if not attrs.get('cedula_pasaporte'):
            raise serializers.ValidationError("La cédula/pasaporte es obligatorio.")
        return attrs
