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
            'is_active',  # 
            'fecha_creacion'
        ]
        read_only_fields = fields

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        try:
            user = Usuario.objects.get(correo__iexact=value, is_active=True)
        except Usuario.DoesNotExist:
            # No revelar si el email existe (seguridad)
            raise serializers.ValidationError("Si el email existe, recibirás instrucciones.")
        return value

class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    uid = serializers.CharField()
    new_password = serializers.CharField(min_length=8)
