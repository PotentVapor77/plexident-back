# patients/models.py
from django.db import models
from django.core.validators import MinLengthValidator, RegexValidator
from django_currentuser.db.models import CurrentUserField
from django.core.exceptions import ValidationError
import uuid
class Paciente(models.Model):
    SEXOS = [
        ('M', 'Masculino'),
        ('F', 'Femenino'),
        ('O', 'Otro'),
    ]

    id = models.UUIDField(primary_key=True,default=uuid.uuid4, editable=False, unique=True)
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    cedula_pasaporte = models.CharField(max_length=20, unique=True)
    fecha_nacimiento = models.DateField()
    sexo = models.CharField(max_length=1, choices=SEXOS)
    direccion = models.CharField(max_length=255, blank=True)
    telefono = models.CharField(
        max_length=20,
        validators=[
            MinLengthValidator(10, message="El número de teléfono debe tener al menos 10 dígitos."),
            RegexValidator(regex=r'^\d{10,}$', message="Solo números, mínimo 10 dígitos.")
        ]
    )
    correo = models.EmailField(blank=True)
    contacto_emergencia_nombre = models.CharField(max_length=100, blank=True)
    contacto_emergencia_telefono = models.CharField(
        max_length=20,
        validators=[
            MinLengthValidator(10, message="El número de teléfono de emergencia debe tener al menos 10 dígitos."),
            RegexValidator(regex=r'^\d{10,}$', message="Solo números, mínimo 10 dígitos.")
        ],
        blank=True
    )
    alergias = models.TextField(blank=True)
    enfermedades_sistemicas = models.TextField(blank=True)
    habitos = models.TextField(blank=True)

    creado_por = CurrentUserField(related_name='%(class)s_creado_por', null=True, blank=True, editable=False)
    actualizado_por = CurrentUserField(on_update=True, related_name='%(class)s_actualizado_por', null=True, blank=True, editable=False)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    activo = models.BooleanField(default=True)

    

    def clean(self):
        if not self.nombres or not self.apellidos:
            raise ValidationError("Los nombres y apellidos son obligatorios.")
        if not self.cedula_pasaporte:
            raise ValidationError("La cédula o pasaporte es obligatorio.")

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"
