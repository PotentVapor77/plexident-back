from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.core.validators import MinLengthValidator, RegexValidator
from django_currentuser.db.models import CurrentUserField
from django.core.exceptions import ValidationError
import bcrypt
import uuid


class UsuarioManager(BaseUserManager):
    def create_user(self, username, correo, password=None, **extra_fields):
        if not username:
            raise ValueError('El usuario debe tener un username')
        if not correo:
            raise ValueError('El usuario debe tener un correo electrónico')
        
        correo = self.normalize_email(correo)
        usuario = self.model(username=username, correo=correo, **extra_fields)
        
        if password:
            usuario.set_password(password)
        
        usuario.save(using=self._db)
        return usuario
    
    def create_superuser(self, username, correo, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('rol', 'Administrador')  
        extra_fields.setdefault('is_active', True)
        
        return self.create_user(username, correo, password, **extra_fields)
    
    def get_by_natural_key(self, username):
        return self.get(username=username)


class Usuario(AbstractBaseUser, PermissionsMixin):
    #  ROLES ACTUALIZADOS
    ROLES = [
        ('Administrador', 'Administrador'),
        ('Odontologo', 'Odontologo'),
        ('Asistente', 'Asistente'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    username = models.CharField(max_length=150, unique=True)
    
    telefono = models.CharField(
        max_length=20,
        validators=[
            MinLengthValidator(10, message="El número de teléfono debe tener al menos 10 dígitos."),
            RegexValidator(regex=r'^\d{10,}$', message="Solo números, mínimo 10 dígitos.")
        ]
    )
    
    correo = models.EmailField(unique=True)
    rol = models.CharField(max_length=20, choices=ROLES, default='Asistente')
    
    # Campos requeridos por Django Admin
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Auditoría
    creado_por = CurrentUserField(
        related_name='%(class)s_creado_por',
        null=True,
        blank=True,
        editable=False
    )
    actualizado_por = CurrentUserField(
        on_update=True,
        related_name='%(class)s_actualizado_por',
        null=True,
        blank=True,
        editable=False
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    reset_password_token = models.CharField(max_length=128,null=True, blank=True,)
    reset_password_expires = models.DateTimeField(null=True, blank=True)
    
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['nombres', 'apellidos', 'correo', 'telefono', 'rol']
    
    objects = UsuarioManager()
    
    def clean(self):
        if not self.nombres or not self.apellidos:
            raise ValidationError("Los nombres y apellidos son obligatorios.")
        if not self.correo:
            raise ValidationError("El correo electrónico es obligatorio.")
        if not self.rol:
            raise ValidationError("Debe asignarse un rol al usuario.")
    
    def set_password(self, password):
        """Hashea la contraseña usando bcrypt"""
        salt = bcrypt.gensalt()
        self.password = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def check_password(self, password):
        """Verifica si la contraseña coincide con el hash"""
        if not self.password:
            return False
        try:
            return bcrypt.checkpw(password.encode('utf-8'), self.password.encode('utf-8'))
        except Exception:
            return False
    

    
    @classmethod
    def authenticate(cls, username, password):
        """Autentica un usuario por username y contraseña"""
        try:
            usuario = cls.objects.get(username=username, activo=True, is_active=True)
            if usuario.check_password(password):
                return usuario
        except cls.DoesNotExist:
            return None
        return None
    
    def get_full_name(self):
        return f"{self.nombres} {self.apellidos}"
    
    def get_short_name(self):
        return self.nombres
    
    def has_perm(self, perm, obj=None):
        """¿Tiene el usuario un permiso específico?"""
        return self.is_staff
    
    def has_module_perms(self, app_label):
        """¿Tiene el usuario permisos para ver la app?"""
        return self.is_staff
    
    def __str__(self):
        return f'{self.username} - {self.nombres} {self.apellidos} ({self.rol})'
    
    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['-fecha_creacion']


# api/users/models.py - AÑADIR después de PermisoRol

class PermisoUsuario(models.Model):
    """Permisos específicos por usuario (no por rol)"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='permisos_usuario')
    modelo = models.CharField(max_length=50)  # 'usuario', 'paciente', 'agenda'
    metodos_permitidos = models.JSONField(default=list)  # ['GET', 'POST']
    #fecha_creacion = models.DateTimeField(auto_now_add=True)
    #fecha_modificacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['usuario', 'modelo']
        verbose_name = 'Permiso de Usuario'
        verbose_name_plural = 'Permisos de Usuarios'
    
    def __str__(self):
        return f"{self.usuario.username} - {self.modelo}: {self.metodos_permitidos}"