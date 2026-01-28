from django.db import models
from django.core.exceptions import ValidationError
from api.patients.models.base import BaseModel
from api.patients.models.paciente import Paciente
from api.patients.models.antecedentes_personales import AntecedentesPersonales
from api.patients.models.antecedentes_familiares import AntecedentesFamiliares
from api.patients.models.constantes_vitales import ConstantesVitales
from api.patients.models.examen_estomatognatico import ExamenEstomatognatico
from api.users.models import Usuario
from .constants import ESTADO_HISTORIAL_CHOICES


class ClinicalRecord(BaseModel):
    """
    Modelo principal de Historial Clínico (Formulario 033).
    Unifica todas las secciones en un solo documento versionado.
    """
    
    # === SECCIÓN A: DATOS DEL PACIENTE (REFERENCIA) ===
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.PROTECT,
        related_name='historiales_clinicos',
        verbose_name='Paciente'
    )
    # === SECCIÓN A: DATOS AUTOMÁTICOS ===
    numero_historia_clinica_unica = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        verbose_name='Número de Historia Clínica Única',
        help_text='Generado automáticamente: HC-{año}{secuencia:05d}'
    )
    
    numero_archivo = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='Número de Archivo',
        help_text='Generado automáticamente: ARCH-{paciente_id[:8]}'
    )
    
    numero_hoja = models.PositiveIntegerField(
        default=1,
        verbose_name='No. Hoja'
    )
    
    institucion_sistema = models.CharField(
        max_length=100,
        default='SISTEMA NACIONAL DE SALUD Temporal',
        verbose_name='Institución del Sistema'
    )
    
    unicodigo = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='UNICÓDIGO'
    )
    
    establecimiento_salud = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Establecimiento de Salud'
    )
    
    # === REFERENCIAS A SECCIONES EXISTENTES ===
    # Estas referencias cargan los últimos datos guardados
    antecedentes_personales = models.ForeignKey(
        AntecedentesPersonales,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historiales_clinicos',
        verbose_name='Antecedentes Personales (Sección D)'
    )
    
    antecedentes_familiares = models.ForeignKey(
        AntecedentesFamiliares,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historiales_clinicos',
        verbose_name='Antecedentes Familiares (Sección E)'
    )
    
    constantes_vitales = models.ForeignKey(
        ConstantesVitales,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historiales_clinicos',
        verbose_name='Constantes Vitales (Sección F)'
    )
    
    examen_estomatognatico = models.ForeignKey(
        ExamenEstomatognatico,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='historiales_clinicos',
        verbose_name='Examen Estomatognático (Sección G)'
    )
    
    # === SECCIÓN B y C: DATOS CLÍNICOS ACTUALES ===
    # Estos campos se copian del paciente pero pueden ser editados antes de guardar
    motivo_consulta = models.TextField(
        blank=True,
        verbose_name='Motivo de Consulta (Sección B)'
    )
    
    embarazada = models.CharField(
        max_length=2,
        choices=[('SI', 'Sí'), ('NO', 'No')],
        blank=True,
        null=True,
        verbose_name='¿Embarazada? (Sección B)'
    )
    
    enfermedad_actual = models.TextField(
        blank=True,
        verbose_name='Enfermedad Actual (Sección C)'
    )
    
    # === METADATA DEL HISTORIAL ===
    estado = models.CharField(
        max_length=10,
        choices=ESTADO_HISTORIAL_CHOICES,
        default='BORRADOR',
        verbose_name='Estado del Historial'
    )
    
    odontologo_responsable = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='historiales_clinicos_responsable',
        limit_choices_to={'rol': 'Odontologo'},
        verbose_name='Odontólogo Responsable'
    )
    
    fecha_atencion = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Atención'
    )
    
    fecha_cierre = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Fecha de Cierre'
    )
    
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones del Profesional'
    )
    
    

    class Meta:
        verbose_name = 'Historial Clínico'
        verbose_name_plural = 'Historiales Clínicos'
        ordering = ['-fecha_atencion']
        indexes = [
            models.Index(fields=['paciente', '-fecha_atencion']),
            models.Index(fields=['estado', 'activo']),
            models.Index(fields=['odontologo_responsable', '-fecha_atencion']),
            models.Index(fields=['numero_historia_clinica_unica']),
        ]
        #constraints = [
            #models.UniqueConstraint(
              #  fields=['paciente', 'numero_archivo'],
              #  name='unique_numero_archivo_per_paciente',
              #  condition=models.Q(activo=True)
            #),
        #]
        
        

    def __str__(self):
        return f"HC-{self.paciente.nombre_completo} - {self.fecha_atencion.strftime('%Y-%m-%d')} - {self.numero_historia_clinica_unica}"

    def clean(self):
        """Validaciones del modelo"""
        super().clean()
        
        # No permitir edición si está cerrado
        if self.pk and self.estado == 'CERRADO':
            old_instance = ClinicalRecord.objects.get(pk=self.pk)
            if old_instance.estado == 'CERRADO':
                raise ValidationError('No se puede editar un historial clínico cerrado.')
        
        # Validar que el odontólogo responsable tenga el rol correcto
        if self.odontologo_responsable and self.odontologo_responsable.rol != 'Odontologo':
            raise ValidationError('El responsable debe ser un odontólogo.')
        
        # Validar embarazo según sexo del paciente
        if self.embarazada == 'SI' and self.paciente.sexo == 'M':
            raise ValidationError('Un paciente masculino no puede estar embarazado.')

    def save(self, *args, **kwargs):
        """Sobrescribe save para aplicar validaciones"""
        self.full_clean()
        super().save(*args, **kwargs)

    def cerrar_historial(self, usuario):
        """
        Cierra el historial clínico, impidiendo futuras ediciones.
        """
        from django.utils import timezone
        
        if self.estado == 'CERRADO':
            raise ValidationError('El historial ya está cerrado.')
        
        self.estado = 'CERRADO'
        self.fecha_cierre = timezone.now()
        self.actualizadopor = usuario
        self.save()

    def reabrir_historial(self, usuario):
        """
        Reabre un historial cerrado (solo para casos excepcionales).
        Requiere permisos especiales.
        """
        if self.estado != 'CERRADO':
            raise ValidationError('Solo se pueden reabrir historiales cerrados.')
        
        self.estado = 'ABIERTO'
        self.fecha_cierre = None
        self.actualizadopor = usuario
        self.save()

    @property
    def puede_editar(self):
        """Verifica si el historial puede ser editado"""
        return self.estado != 'CERRADO' and self.activo

    @property
    def esta_completo(self):
        """Verifica si el historial tiene todas las secciones completas"""
        return all([
            self.motivo_consulta,
            self.antecedentes_personales,
            self.antecedentes_familiares,
            self.constantes_vitales,
            self.examen_estomatognatico
        ])
    constantes_vitales_nuevas = models.BooleanField(
        default=False,
        verbose_name='¿Constantes vitales nuevas?'
    )
    
    motivo_consulta_nuevo = models.BooleanField(
        default=False,
        verbose_name='¿Motivo de consulta nuevo?'
    )
    
    enfermedad_actual_nueva = models.BooleanField(
        default=False,
        verbose_name='¿Enfermedad actual nueva?'
    )
    
    