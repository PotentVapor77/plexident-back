# api/clinical_records/models/form033_snapshot.py
"""
Modelo para almacenar snapshots del Formulario 033 (Odontograma)
asociados a historiales clínicos
"""
from django.db import models
from api.patients.models.base import BaseModel
from api.users.models import Usuario


class Form033Snapshot(BaseModel):
    """
    Snapshot del Formulario 033 en el momento de crear/actualizar el historial clínico.
    Almacena el estado completo del odontograma del paciente.
    """
    
    # Relación con el historial clínico
    historial_clinico = models.OneToOneField(
        'ClinicalRecord',
        on_delete=models.CASCADE,
        related_name='form033_snapshot',
        verbose_name='Historial Clínico Asociado'
    )
    
    # Datos JSON del Form033 (estructura completa)
    datos_form033 = models.JSONField(
        verbose_name='Datos del Formulario 033',
        help_text='Estructura JSON completa del odontograma (permanente y temporal)'
    )
    
    # Metadatos de la captura
    fecha_captura = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de Captura'
    )
    
    capturado_por = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name='form033_snapshots_capturados',
        verbose_name='Capturado por'
    )
    
    # Estadísticas del snapshot (para búsquedas rápidas)
    total_dientes_permanentes = models.PositiveIntegerField(
        default=0,
        verbose_name='Total Dientes Permanentes con Diagnóstico'
    )
    
    total_dientes_temporales = models.PositiveIntegerField(
        default=0,
        verbose_name='Total Dientes Temporales con Diagnóstico'
    )
    
    total_caries = models.PositiveIntegerField(
        default=0,
        verbose_name='Total Caries Detectadas'
    )
    
    total_ausentes = models.PositiveIntegerField(
        default=0,
        verbose_name='Total Dientes Ausentes'
    )
    
    total_obturados = models.PositiveIntegerField(
        default=0,
        verbose_name='Total Dientes Obturados'
    )
    
    # Observaciones adicionales
    observaciones = models.TextField(
        blank=True,
        verbose_name='Observaciones del Odontograma'
    )
    
    
    class Meta:
        verbose_name = 'Snapshot Formulario 033'
        verbose_name_plural = 'Snapshots Formulario 033'
        ordering = ['-fecha_captura']
        indexes = [
            models.Index(fields=['historial_clinico']),
            models.Index(fields=['fecha_captura']),
            models.Index(fields=['capturado_por', '-fecha_captura']),
        ]
    
    
    def __str__(self):
        return f"Form033 - HC: {self.historial_clinico.numero_historia_clinica_unica} - {self.fecha_captura.strftime('%Y-%m-%d %H:%M')}"
    
    
    def calcular_estadisticas(self):
        """
        Calcula y actualiza las estadísticas del snapshot basándose en los datos JSON
        """
        if not self.datos_form033:
            return
        
        # Extraer datos del odontograma
        odontograma_permanente = self.datos_form033.get('odontograma_permanente', {})
        odontograma_temporal = self.datos_form033.get('odontograma_temporal', {})
        
        # Contar dientes permanentes
        dientes_perm = odontograma_permanente.get('dientes', [])
        self.total_dientes_permanentes = sum(
            1 for fila in dientes_perm 
            for diente in fila 
            if diente is not None
        )
        
        # Contar dientes temporales
        dientes_temp = odontograma_temporal.get('dientes', [])
        self.total_dientes_temporales = sum(
            1 for fila in dientes_temp 
            for diente in fila 
            if diente is not None
        )
        
        # Contar tipos específicos
        self.total_caries = 0
        self.total_ausentes = 0
        self.total_obturados = 0
        
        # Función helper para contar
        def contar_tipos(matriz_dientes):
            caries = 0
            ausentes = 0
            obturados = 0
            
            for fila in matriz_dientes:
                for diente in fila:
                    if not diente:
                        continue
                    
                    key = diente.get('key', '')
                    
                    if key == 'caries':
                        caries += 1
                    elif key == 'ausente':
                        ausentes += 1
                    elif key == 'obturacion':
                        obturados += 1
            
            return caries, ausentes, obturados
        
        # Contar permanentes
        c_perm, a_perm, o_perm = contar_tipos(dientes_perm)
        # Contar temporales
        c_temp, a_temp, o_temp = contar_tipos(dientes_temp)
        
        # Totalizar
        self.total_caries = c_perm + c_temp
        self.total_ausentes = a_perm + a_temp
        self.total_obturados = o_perm + o_temp
    
    
    def save(self, *args, **kwargs):
        """Override save para calcular estadísticas automáticamente"""
        if self.datos_form033:
            self.calcular_estadisticas()
        super().save(*args, **kwargs)
    
    
    @property
    def resumen_estadistico(self):
        """Retorna un resumen legible de las estadísticas"""
        total_dientes = self.total_dientes_permanentes + self.total_dientes_temporales
        
        return {
            'total_dientes_con_diagnostico': total_dientes,
            'permanentes': self.total_dientes_permanentes,
            'temporales': self.total_dientes_temporales,
            'caries': self.total_caries,
            'ausentes': self.total_ausentes,
            'obturados': self.total_obturados,
        }
