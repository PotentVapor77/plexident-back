from rest_framework import serializers
from .models import Usuario
from django.contrib.auth import get_user_model

class UsuarioSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=8)
    
    class Meta:
        model = Usuario
        fields = [
            'id', 'nombres', 'apellidos', 'username', 
            'telefono', 'correo', 'password', 'rol', 'activo',
            'creado_por', 'actualizado_por', 'fecha_creacion', 'fecha_modificacion'
        ]
        read_only_fields = [
            'id', 'creado_por', 'actualizado_por', 
            'fecha_creacion', 'fecha_modificacion', 'username'
        ]

    

    def create(self, validated_data):
    
        """Simplificar el create"""
        password = validated_data.pop('password', None)
        usuario = Usuario.objects.create(**validated_data)
        if password:
            usuario.set_password(password)
            usuario.save()
        return usuario

    def update(self, instance, validated_data):
        """Simplificar el update"""
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)