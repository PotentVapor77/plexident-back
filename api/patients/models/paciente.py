# patients/models/paciente.py
from django.db import models
from django.core.validators import MinLengthValidator, RegexValidator
from django.core.exceptions import ValidationError
from .base import BaseModel
from .constants import SEXOS, CONDICION_EDAD, EMBARAZADA_CHOICES

class Paciente(BaseModel):
    """Modelo principal para los pacientes"""
    
    # ================== SECCIÓN A: DATOS PERSONALES ==================
    # Campos correctos: solo nombres y apellidos
    nombres = models.CharField(max_length=100, verbose_name="Nombres completos")
    apellidos = models.CharField(max_length=100, verbose_name="Apellidos completos")
    
    sexo = models.CharField(max_length=1, choices=SEXOS, verbose_name="Sexo")
    edad = models.PositiveIntegerField(verbose_name="Edad")
    condicion_edad = models.CharField(max_length=1, choices=CONDICION_EDAD, verbose_name="Condición de edad")
    embarazada = models.CharField(max_length=2, choices=EMBARAZADA_CHOICES, blank=True, null=True, verbose_name="Embarazada")
    
    # Datos de identificación
    cedula_pasaporte = models.CharField(max_length=20, unique=True, verbose_name="Cédula/Pasaporte")
    fecha_nacimiento = models.DateField(verbose_name="Fecha de nacimiento")
    fecha_ingreso = models.DateField(verbose_name="Fecha de ingreso")
    direccion = models.CharField(max_length=255, blank=True, verbose_name="Dirección")
    telefono = models.CharField(
        max_length=20,
        validators=[
            MinLengthValidator(10, message="El número de teléfono debe tener al menos 10 dígitos."),
            RegexValidator(regex=r'^\d{10,}$', message="Solo números, mínimo 10 dígitos.")
        ],
        verbose_name="Teléfono"
    )
    correo = models.EmailField(blank=True, verbose_name="Correo electrónico")
    
    contacto_emergencia_nombre = models.CharField(max_length=100, blank=True, verbose_name="Contacto de emergencia - Nombre")
    contacto_emergencia_telefono = models.CharField(
        max_length=20,
        validators=[
            MinLengthValidator(10, message="El número de teléfono de emergencia debe tener al menos 10 dígitos."),
            RegexValidator(regex=r'^\d{10,}$', message="Solo números, mínimo 10 dígitos.")
        ],
        blank=True,
        verbose_name="Contacto de emergencia - Teléfono"
    )
    
    

  
    class Meta:
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"
        ordering = ['apellidos', 'nombres']  
        indexes = [
            models.Index(fields=['apellidos', 'nombres']),  
            models.Index(fields=['activo']),
        ]
        
    def get_full_name(self):
         """Retorna el nombre completo del paciente"""
         return f"{self.apellidos}, {self.nombres}".strip()
    
    def __str__(self):
        return self.get_full_name()


    def clean(self):
        """Validaciones del formulario"""
        if not self.nombres or not self.apellidos:  
            raise ValidationError("Los nombres y apellidos son obligatorios.")
        if not self.cedula_pasaporte:
            raise ValidationError("La cédula o pasaporte es obligatorio.")
        
        # Validación: si es hombre, no puede estar embarazado
        if self.sexo == 'M' and self.embarazada == 'SI':
            raise ValidationError("Un paciente masculino no puede estar marcado como embarazado.")
        
        # Validación: edad y condición de edad
        if self.edad and not self.condicion_edad:
            raise ValidationError("Debe especificar la condición de edad (horas, días, meses, años).")
    
    def save(self, *args, **kwargs):
        """Método save con validaciones automáticas"""
        if self.sexo == 'M':
            self.embarazada = None
        
        self.full_clean()
        super().save(*args, **kwargs)
    
    def __str__(self):
        """Representación en string del paciente"""
        return f"{self.nombre_completo} - {self.cedula_pasaporte}"
    
    # ================== PROPIEDADES ÚTILES ==================
    @property
    def nombre_completo(self):
        """Retorna el nombre completo del paciente"""
        return f"{self.apellidos}, {self.nombres}".strip()  
    
    @property
    def edad_completa(self):
        """Retorna la edad con su condición"""
        if self.edad and self.condicion_edad:
            condicion = dict(CONDICION_EDAD).get(self.condicion_edad)
            return f"{self.edad} {condicion}"
        return ""
