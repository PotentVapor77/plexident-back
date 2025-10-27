from rest_framework import serializers
from .models import Usuario

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = '__all__'
        read_only_fields = ['created_by', 'updated_by', 'created_at', 'updated_at']

    def validate_contrasena_hash(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("La contraseña debe tener al menos 8 caracteres.")
        return value

    def validate(self, attrs):
        if attrs.get('rol') not in ['admin', 'odontologo', 'asistente']:
            raise serializers.ValidationError("El rol no es válido.")
        return attrs
