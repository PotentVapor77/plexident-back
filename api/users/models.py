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
        extra_fields.setdefault('rol', 'Administrador')  # ✅ Actualizado
        extra_fields.setdefault('activo', True)
        
        return self.create_user(username, correo, password, **extra_fields)
    
    def get_by_natural_key(self, username):
        return self.get(username=username)


class Usuario(AbstractBaseUser, PermissionsMixin):
    # ✅ ROLES ACTUALIZADOS
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
    
    #  Campo activo (o usar is_active directamente)
    activo = models.BooleanField(default=True)
    
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
    
    def save(self, *args, **kwargs):
        # Sincronizar activo con is_active
        self.is_active = self.activo
        
        # Si la contraseña parece estar en texto plano, hashearla
        if self.password and len(self.password) < 60:
            self.set_password(self.password)
        
        super().save(*args, **kwargs)
    
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
