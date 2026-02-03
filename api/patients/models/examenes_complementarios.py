# api/patients/models/anamnesis/examenes_complementarios.py

from django.db import models
from django.core.exceptions import ValidationError

from api.patients.models.paciente import Paciente
from .base import BaseModel
from .constants import INFORME_EXAMENES_CHOICES, PEDIDO_EXAMENES_CHOICES


class ExamenesComplementarios(BaseModel):
    """
    Exámenes complementarios solicitados y realizados (Sección L).
    Relación ForeignKey para permitir múltiples registros por paciente.
    """
    
    # ✅ Relación ForeignKey (1 a muchos)
    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name='examenes_complementarios',
        verbose_name="Paciente"
    )
    
    # PEDIDO DE EXÁMENES
    pedido_examenes = models.CharField(
        max_length=2,
        choices=PEDIDO_EXAMENES_CHOICES,
        default='NO',
        verbose_name="Solicitud de exámenes complementarios"
    )
    
    pedido_examenes_detalle = models.TextField(
        blank=True,
        verbose_name="Detalle de exámenes solicitados",
        help_text="Especificar qué exámenes se solicitan y por qué (ej: radiografía, hemograma, etc.)"
    )
    
    # INFORME DE EXÁMENES
    informe_examenes = models.CharField(
        max_length=20,
        choices=INFORME_EXAMENES_CHOICES,
        default='NINGUNO',
        verbose_name="Informe de exámenes realizados"
    )
    
    informe_examenes_detalle = models.TextField(
        blank=True,
        verbose_name="Resultados de exámenes",
        help_text="Detallar resultados de los exámenes realizados"
    )
    
    class Meta:
        verbose_name = "Examen Complementario"
        verbose_name_plural = "Exámenes Complementarios"
        ordering = ['-fecha_modificacion']
        indexes = [
            models.Index(fields=['paciente']),
            models.Index(fields=['pedido_examenes']),
            models.Index(fields=['informe_examenes']),
        ]
    
    def __str__(self):
        return f"Exámenes Complementarios - {self.paciente.nombre_completo}"
    
    def clean(self):
        """Validaciones personalizadas"""
        errors = {}
        
        # Validar pedido de exámenes
        if self.pedido_examenes == 'SI' and not self.pedido_examenes_detalle:
            errors['pedido_examenes_detalle'] = 'Debe especificar los exámenes solicitados'
        
        # Validar informe de exámenes "OTROS"
        if self.informe_examenes == 'OTROS' and not self.informe_examenes_detalle:
            errors['informe_examenes_detalle'] = 'Debe especificar el tipo de examen cuando selecciona "Otros"'
        
        # Validar que si hay informe, debe tener detalle
        if self.informe_examenes != 'NINGUNO' and not self.informe_examenes_detalle:
            errors['informe_examenes_detalle'] = 'Debe detallar los resultados del examen'
        
        if errors:
            raise ValidationError(errors)
    
    @property
    def tiene_pedido_examenes_pendiente(self):
        """Verifica si hay exámenes complementarios pendientes"""
        return self.pedido_examenes == 'SI'
    
    @property
    def tiene_informe_examenes_completado(self):
        """Verifica si hay informes de exámenes completados"""
        return self.informe_examenes != 'NINGUNO' and bool(self.informe_examenes_detalle)
    
    @property
    def resumen_examenes_complementarios(self):
        """Resumen de la sección de exámenes"""
        resumen = []
        
        if self.tiene_pedido_examenes_pendiente:
            resumen.append("Exámenes solicitados")
            if self.pedido_examenes_detalle:
                detalle = self.pedido_examenes_detalle[:50]
                if len(self.pedido_examenes_detalle) > 50:
                    detalle += "..."
                resumen.append(f"({detalle})")
        
        if self.tiene_informe_examenes_completado:
            tipo_examen = self.get_informe_examenes_display().lower()
            resumen.append(f"Informe de {tipo_examen} completado")
        
        return " - ".join(resumen) if resumen else "Sin exámenes complementarios"
    
    @property
    def estado_examenes(self):
        """Estado general de los exámenes complementarios"""
        if self.tiene_informe_examenes_completado:
            return "completado"
        elif self.tiene_pedido_examenes_pendiente:
            return "pendiente"
        else:
            return "no_solicitado"
    
    def marcar_examenes_solicitados(self, detalle=None):
        """Método para marcar exámenes como solicitados"""
        self.pedido_examenes = 'SI'
        if detalle:
            self.pedido_examenes_detalle = detalle
        self.save()
    
    def agregar_resultado_examen(self, tipo_examen, resultado):
        """Método para agregar resultados de exámenes"""
        self.informe_examenes = tipo_examen
        self.informe_examenes_detalle = resultado
        self.save()
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)