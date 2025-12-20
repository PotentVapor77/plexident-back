# patients/models/base.py

#Modelo base con campos comunes
import uuid
from django.db import models
from django_currentuser.db.models import CurrentUserField

class BaseModel(models.Model):
    """Modelo base abstracto con campos comunes a todos los modelos"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    
    creado_por = CurrentUserField(
        related_name='%(class)s_creado_por', 
        null=True, 
        blank=True, 
        editable=False,
        verbose_name="Creado por"
    )
    
    actualizado_por = CurrentUserField(
        on_update=True, 
        related_name='%(class)s_actualizado_por', 
        null=True, 
        blank=True, 
        editable=False,
        verbose_name="Actualizado por"
    )
    
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    fecha_modificacion = models.DateTimeField(auto_now=True, verbose_name="Fecha de modificación")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    
    class Meta:
        abstract = True