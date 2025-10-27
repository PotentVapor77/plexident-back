from django.db import models
from django.core.validators import MinLengthValidator, RegexValidator
from django_currentuser.db.models import CurrentUserField
from django.core.exceptions import ValidationError

class Usuario(models.Model):
    ROLES = [
        ('admin', 'Administrador'),
        ('odontologo', 'Odontólogo'),
        ('asistente', 'Asistente'),
    ]

    id_usuario = models.AutoField(primary_key=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    username = models.CharField(max_length=150, unique=True, blank=True)
    imagen_perfil = models.ImageField(upload_to='usuarios/perfiles/', blank=True, null=True)

    telefono = models.CharField(
        max_length=20,
        validators=[
            MinLengthValidator(10, message="El número de teléfono debe tener al menos 10 dígitos."),
            RegexValidator(regex=r'^\d{10,}$', message="Solo números, mínimo 10 dígitos.")
        ]
    )

    correo = models.EmailField(unique=True)
    contrasena_hash = models.CharField(max_length=128, validators=[MinLengthValidator(8)])
    
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

    def save(self, *args, **kwargs):
        # Generar username automáticamente si está vacío
        if not self.username:
            first_initial = self.nombres[0].lower() if self.nombres else ""
            first_surname = self.apellidos.split()[0].lower() if self.apellidos else ""
            base_username = f"{first_initial}{first_surname}"
            self.username = self.generate_unique_username(base_username)
        super().save(*args, **kwargs)

    def generate_unique_username(self, base_username):
        counter = 0
        new_username = base_username
        while Usuario.objects.filter(username=new_username).exists():
            counter += 1
            new_username = f"{base_username}{counter}"
        return new_username

    def __str__(self):
        return f'{self.username} - {self.nombres} {self.apellidos} ({self.rol})'
