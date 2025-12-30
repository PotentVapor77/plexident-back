from rest_framework import serializers
from .models import  PermisoUsuario, Usuario
import re

class UsuarioSerializer(serializers.ModelSerializer):
    """Serializer para lectura de usuarios"""
    class Meta:
        model = Usuario
        fields = [
            'id', 'nombres', 'apellidos', 'username',
            'telefono', 'correo', 'rol','is_active',
            'creado_por', 'actualizado_por',
            'fecha_creacion', 'fecha_modificacion'
        ]
        read_only_fields = [
            'id', 'creado_por', 'actualizado_por',
            'fecha_creacion', 'fecha_modificacion'
        ]


class UsuarioCreateSerializer(serializers.ModelSerializer):
    """Serializer para creación de usuarios"""
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        min_length=8,  #  Frontend exige 8
        error_messages={
            'min_length': 'La contraseña debe tener al menos 8 caracteres.',
            'required': 'La contraseña es requerida.'
        }
    )
    
    username = serializers.CharField(
        required=False,
        min_length=4,
        help_text='Si no se proporciona, se generará automáticamente'
    )
    
    class Meta:
        model = Usuario
        fields = [
            'nombres', 'apellidos', 'username', 'telefono',
            'correo', 'rol', 'password', 'is_active',
        ]
    
    def validate_nombres(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("El nombre es requerido.")
        return value.strip()
    
    def validate_apellidos(self, value):
        if not value or len(value.strip()) == 0:
            raise serializers.ValidationError("El apellido es requerido.")
        return value.strip()
    
    def validate_username(self, value):
        """Validar username si se proporciona"""
        if value:
            if len(value) < 4:
                raise serializers.ValidationError(
                    "El username debe tener al menos 4 caracteres."
                )
            if Usuario.objects.filter(username=value).exists():
                raise serializers.ValidationError(
                    "Este username ya está en uso."
                )
        return value
    
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
        
        #  ROLES ACTUALIZADOS
        roles_validos = ['Administrador', 'Odontologo', 'Asistente']
        if value not in roles_validos:
            raise serializers.ValidationError(
                f"Rol inválido. Los roles válidos son: {', '.join(roles_validos)}"
            )
        return value
    
     
    def create(self, validated_data):
        password = validated_data.pop('password')
        
        # Respaldo: generar username solo si NO viene del frontend
        if not validated_data.get('username'):
            import unicodedata
            import re
            
            nombres = validated_data['nombres'].strip()
            apellidos = validated_data['apellidos'].strip()
            
            primera_letra = nombres.split()[0][0].lower() if nombres else ''
            primer_apellido = apellidos.split()[0] if apellidos else ''
            
            # Normalizar (remover acentos)
            primer_apellido_normalizado = unicodedata.normalize('NFD', primer_apellido.lower())
            primer_apellido_normalizado = re.sub(r'[\u0300-\u036f]', '', primer_apellido_normalizado)
            primer_apellido_normalizado = re.sub(r'[^a-z0-9]', '', primer_apellido_normalizado)
            
            base_username = f"{primera_letra}{primer_apellido_normalizado}"
            username = base_username
            counter = 1
            
            while Usuario.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            validated_data['username'] = username
        
        usuario = Usuario.objects.create(**validated_data)
        usuario.set_password(password)
        usuario.save()
        return usuario



class UsuarioUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualización de usuarios"""
    password = serializers.CharField(
        write_only=True,
        required=False,  #  NO obligatorio en update
        style={'input_type': 'password'},
        min_length=8,
        allow_blank=True,
        help_text='Dejar en blanco para mantener la contraseña actual'
    )
    
    class Meta:
        model = Usuario
        fields = [
            'nombres', 'apellidos', 'telefono', 'correo',
            'rol','is_active','password'
        ]
        read_only_fields = ['username']  #  Username no se puede cambiar
    
    def validate_telefono(self, value):
        if not value:
            raise serializers.ValidationError("El teléfono es requerido.")
        if not re.match(r'^\d{10,}$', value):
            raise serializers.ValidationError(
                "El teléfono debe contener solo números y tener al menos 10 dígitos."
            )
        return value
    
    def validate_correo(self, value):
        if not value:
            raise serializers.ValidationError("El correo electrónico es requerido.")
        
        # Verificar si el correo ya existe (excepto el usuario actual)
        usuario_actual = self.instance
        if Usuario.objects.filter(correo=value).exclude(pk=usuario_actual.pk).exists():
            raise serializers.ValidationError("Este correo electrónico ya está registrado.")
        
        return value
    
    def validate_rol(self, value):
        if not value:
            raise serializers.ValidationError("El rol es requerido.")
        
        roles_validos = ['Administrador', 'Odontologo', 'Asistente']
        if value not in roles_validos:
            raise serializers.ValidationError(
                f"Rol inválido. Los roles válidos son: {', '.join(roles_validos)}"
            )
        return value
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        
        # Actualizar campos
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Solo cambiar password si se proporciona
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance


#permiso por usuario
class PermisoUsuarioSerializer(serializers.ModelSerializer):
    usuario_id = serializers.UUIDField(source='usuario.id', read_only=True)
    usuario_nombre = serializers.CharField(source='usuario.get_full_name', read_only=True)
    usuario_rol = serializers.CharField(source='usuario.rol', read_only=True)
    
    class Meta:
        model = PermisoUsuario
        fields = ['id', 'usuario_id', 'usuario_nombre', 'usuario_rol', 'modelo', 'metodos_permitidos']



class PermisoUsuarioCreateUpdateSerializer(serializers.ModelSerializer):
    usuario_id = serializers.UUIDField(write_only=True, required=True)

    class Meta:
        model = PermisoUsuario
        fields = ['usuario_id', 'modelo', 'metodos_permitidos']

    def validate_usuario_id(self, value):
        try:
            usuario = Usuario.objects.get(id=value)
            
            #  VALIDAR: No permitir asignar permisos a Administradores
            if usuario.rol == 'Administrador':
                raise serializers.ValidationError(
                    "No se pueden asignar permisos a usuarios Administradores"
                )
            
            return value
        except Usuario.DoesNotExist:
            raise serializers.ValidationError("Usuario no encontrado")

    def create(self, validated_data):
        usuario_id = validated_data.pop('usuario_id')
        usuario = Usuario.objects.get(id=usuario_id)
        
        #  OPTIMIZACIÓN: No crear si metodos_permitidos está vacío
        metodos = validated_data.get('metodos_permitidos', [])
        if not metodos:
            return None  # O lanzar excepción si prefieres
        
        return PermisoUsuario.objects.create(usuario=usuario, **validated_data)

    def update(self, instance, validated_data):
        usuario_id = validated_data.pop('usuario_id', None)
        if usuario_id:
            usuario = Usuario.objects.get(id=usuario_id)
            instance.usuario = usuario
        return super().update(instance, validated_data)