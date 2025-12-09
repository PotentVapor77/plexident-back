from rest_framework import serializers
from .models import Usuario
import re

class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = [
            'id', 'nombres', 'apellidos', 'username', 
            'telefono', 'correo', 'rol', 'activo',
            'creado_por', 'actualizado_por', 'fecha_creacion', 'fecha_modificacion'
        ]
        read_only_fields = [
            'id', 'username', 'creado_por', 'actualizado_por', 
            'fecha_creacion', 'fecha_modificacion'
        ]

class UsuarioCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, 
        required=True,
        style={'input_type': 'password'},
        min_length=6,
        error_messages={
            'min_length': 'La contraseña debe tener al menos 6 caracteres.',
            'required': 'La contraseña es requerida.'
        }
    )

    class Meta:
        model = Usuario
        fields = ['nombres', 'apellidos', 'telefono', 'correo', 'rol', 'password']
    
    def validate_nombres(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("El nombre es requerido.")
        return value.strip()
    
    def validate_apellidos(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("El apellido es requerido.")
        return value.strip()
    
    def validate_telefono(self, value):
        if not value:
            raise serializers.ValidationError("El teléfono es requerido.")
        
        # Validar formato
        if not re.match(r'^\d{10,}$', value):
            raise serializers.ValidationError(
                "El teléfono debe contener solo números y tener al menos 10 dígitos."
            )
        return value
    
    def validate_correo(self, value):
        if not value:
            raise serializers.ValidationError("El correo electrónico es requerido.")
        
        # Verificar si el correo ya existe
        if Usuario.objects.filter(correo=value).exists():
            raise serializers.ValidationError("Este correo electrónico ya está registrado.")
        return value
    
    def validate_rol(self, value):
        if not value:
            raise serializers.ValidationError("El rol es requerido.")
        
        roles_validos = ['admin', 'odontologo', 'asistente']
        if value not in roles_validos:
            raise serializers.ValidationError(
                f"Rol inválido. Los roles válidos son: {', '.join(roles_validos)}"
            )
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        usuario = Usuario.objects.create(**validated_data)
        usuario.set_password(password)
        usuario.save()
        return usuario

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(
        required=True,
        error_messages={
            'required': 'El nombre de usuario es requerido.'
        }
    )
    password = serializers.CharField(
        required=True,
        style={'input_type': 'password'},
        error_messages={
            'required': 'La contraseña es requerida.'
        }
    )