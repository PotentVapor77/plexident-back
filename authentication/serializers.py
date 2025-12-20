from rest_framework import serializers
from api.users.models import Usuario


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(
        required=True,
        error_messages={'required': 'El nombre de usuario es requerido.'}
    )
    
    password = serializers.CharField(
        required=True,
        style={'input_type': 'password'},
        write_only=True,
        error_messages={'required': 'La contraseña es requerida.'}
    )


class AuthUserSerializer(serializers.ModelSerializer):
    """Serializer para respuesta auth con rol"""
    
    class Meta:
        model = Usuario
        fields = [
            'id',
            'username',
            'nombres',
            'apellidos',
            'correo',
            'telefono',
            'rol',
            'activo',  # ✅ Cambiar a 'activo' (campo principal del modelo)
            'fecha_creacion'
        ]
        read_only_fields = fields
