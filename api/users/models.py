from django.db import models
from django.core.validators import MinLengthValidator, RegexValidator
from django_currentuser.db.models import CurrentUserField
from django.core.exceptions import ValidationError
import bcrypt
import uuid

class Usuario(models.Model):
    ROLES = [
        ('admin', 'Administrador'),
        ('odontologo', 'Odontólogo'),
        ('asistente', 'Asistente'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    username = models.CharField(max_length=150, unique=True, blank=True)

    telefono = models.CharField(
        max_length=20,
        validators=[
            MinLengthValidator(10, message="El número de teléfono debe tener al menos 10 dígitos."),
            RegexValidator(regex=r'^\d{10,}$', message="Solo números, mínimo 10 dígitos.")
        ]
    )

    correo = models.EmailField(unique=True)
    contrasena_hash = models.CharField(max_length=255)  # Aumentado para bcrypt
    
    rol = models.CharField(max_length=20, choices=ROLES)
    created_by = CurrentUserField(related_name='%(class)s_created_by', null=True, blank=True, editable=False)
    updated_by = CurrentUserField(on_update=True, related_name='%(class)s_updated_by', null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)

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
        self.contrasena_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def check_password(self, password):
        """Verifica si la contraseña coincide con el hash"""
        if not self.contrasena_hash:
            return False
        try:
            return bcrypt.checkpw(password.encode('utf-8'), self.contrasena_hash.encode('utf-8'))
        except Exception:
            return False

    def save(self, *args, **kwargs):
        # Generar username automáticamente si está vacío
        if not self.username:
            first_initial = self.nombres[0].lower() if self.nombres else ""
            first_surname = self.apellidos.split()[0].lower() if self.apellidos else ""
            base_username = f"{first_initial}{first_surname}"
            self.username = self.generate_unique_username(base_username)
        
        # Si la contraseña parece estar en texto plano (menos de 60 chars), hashearla
        if self.contrasena_hash and len(self.contrasena_hash) < 60:
            self.set_password(self.contrasena_hash)
            
        super().save(*args, **kwargs)

    def generate_unique_username(self, base_username):
        counter = 0
        new_username = base_username
        while Usuario.objects.filter(username=new_username).exists():
            counter += 1
            new_username = f"{base_username}{counter}"
        return new_username

    @classmethod
    def authenticate(cls, username, password):
        """Autentica un usuario por username y contraseña"""
        try:
            usuario = cls.objects.get(username=username, status=True)
            if usuario.check_password(password):
                return usuario
        except cls.DoesNotExist:
            return None
        return None

    def __str__(self):
        return f'{self.username} - {self.nombres} {self.apellidos} ({self.rol})'