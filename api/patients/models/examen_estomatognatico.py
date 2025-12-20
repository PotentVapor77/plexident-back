# patients/models/examen_estomatognatico.py
from django.db import models
from .base import BaseModel
from .paciente import Paciente
from .constants import ESTADO_EXAMEN

class ExamenEstomatognatico(BaseModel):
    """Examen del sistema estomatognático (Sección G)"""
    
    paciente = models.OneToOneField(
        Paciente,
        on_delete=models.CASCADE,
        related_name='examen_estomatognatico',
        verbose_name="Paciente"
    )
    
    # 1. LABIOS
    examen_labios = models.CharField(
        max_length=20,
        choices=ESTADO_EXAMEN,
        default='NO_EXAMINADO',
        verbose_name="Labios"
    )
    examen_labios_descripcion = models.TextField(blank=True, verbose_name="Descripción labios")
    
    # 2. MEJILLAS
    examen_mejillas = models.CharField(
        max_length=20,
        choices=ESTADO_EXAMEN,
        default='NO_EXAMINADO',
        verbose_name="Mejillas"
    )
    examen_mejillas_descripcion = models.TextField(blank=True, verbose_name="Descripción mejillas")
    
    # 3. MAXILAR SUPERIOR
    examen_maxilar_superior = models.CharField(
        max_length=20,
        choices=ESTADO_EXAMEN,
        default='NO_EXAMINADO',
        verbose_name="Maxilar superior"
    )
    examen_maxilar_superior_descripcion = models.TextField(blank=True, verbose_name="Descripción maxilar superior")
    
    # 4. MAXILAR INFERIOR
    examen_maxilar_inferior = models.CharField(
        max_length=20,
        choices=ESTADO_EXAMEN,
        default='NO_EXAMINADO',
        verbose_name="Maxilar inferior"
    )
    examen_maxilar_inferior_descripcion = models.TextField(blank=True, verbose_name="Descripción maxilar inferior")
    
    # 5. LENGUA
    examen_lengua = models.CharField(
        max_length=20,
        choices=ESTADO_EXAMEN,
        default='NO_EXAMINADO',
        verbose_name="Lengua"
    )
    examen_lengua_descripcion = models.TextField(blank=True, verbose_name="Descripción lengua")
    
    # 6. PALADAR
    examen_paladar = models.CharField(
        max_length=20,
        choices=ESTADO_EXAMEN,
        default='NO_EXAMINADO',
        verbose_name="Paladar"
    )
    examen_paladar_descripcion = models.TextField(blank=True, verbose_name="Descripción paladar")
    
    # 7. PISO DE LA BOCA
    examen_piso_boca = models.CharField(
        max_length=20,
        choices=ESTADO_EXAMEN,
        default='NO_EXAMINADO',
        verbose_name="Piso de la boca"
    )
    examen_piso_boca_descripcion = models.TextField(blank=True, verbose_name="Descripción piso de la boca")
    
    # 8. CARRILLOS
    examen_carrillos = models.CharField(
        max_length=20,
        choices=ESTADO_EXAMEN,
        default='NO_EXAMINADO',
        verbose_name="Carrillos"
    )
    examen_carrillos_descripcion = models.TextField(blank=True, verbose_name="Descripción carrillos")
    
    # 9. (Sin etiqueta en el Excel)
    examen_region_9 = models.CharField(
        max_length=20,
        choices=ESTADO_EXAMEN,
        default='NO_EXAMINADO',
        verbose_name="Región 9"
    )
    examen_region_9_descripcion = models.TextField(blank=True, verbose_name="Descripción región 9")
    
    # 10. GLÁNDULAS SALIVALES
    examen_glandulas_salivales = models.CharField(
        max_length=20,
        choices=ESTADO_EXAMEN,
        default='NO_EXAMINADO',
        verbose_name="Glándulas salivales"
    )
    examen_glandulas_salivales_descripcion = models.TextField(blank=True, verbose_name="Descripción glándulas salivales")
    
    # 10. ORO FARINGE
    examen_oro_faringe = models.CharField(
        max_length=20,
        choices=ESTADO_EXAMEN,
        default='NO_EXAMINADO',
        verbose_name="Orofaringe"
    )
    examen_oro_faringe_descripcion = models.TextField(blank=True, verbose_name="Descripción orofaringe")
    
    # 11. A.T.M. (Articulación Temporomandibular)
    examen_atm = models.CharField(
        max_length=20,
        choices=ESTADO_EXAMEN,
        default='NO_EXAMINADO',
        verbose_name="A.T.M."
    )
    examen_atm_descripcion = models.TextField(blank=True, verbose_name="Descripción A.T.M.")
    
    # 12. GANGLIOS
    examen_ganglios = models.CharField(
        max_length=20,
        choices=ESTADO_EXAMEN,
        default='NO_EXAMINADO',
        verbose_name="Ganglios"
    )
    examen_ganglios_descripcion = models.TextField(blank=True, verbose_name="Descripción ganglios")
    
    # 13. OTROS
    examen_otros = models.TextField(blank=True, verbose_name="Otros hallazgos")
    
    class Meta:
        verbose_name = "Examen Estomatognático"
        verbose_name_plural = "Exámenes Estomatognáticos"
        ordering = ['paciente__apellidos', 'paciente__nombres']
    
    def __str__(self):
        return f"Examen estomatognático de {self.paciente.nombre_completo}"
    
    @property
    def areas_anormales(self):
        """Retorna lista de áreas con examen anormal"""
        areas_anormales = []
        
        # Lista de todos los campos de examen
        campos_examen = [
            ('Labios', self.examen_labios, self.examen_labios_descripcion),
            ('Mejillas', self.examen_mejillas, self.examen_mejillas_descripcion),
            ('Maxilar superior', self.examen_maxilar_superior, self.examen_maxilar_superior_descripcion),
            ('Maxilar inferior', self.examen_maxilar_inferior, self.examen_maxilar_inferior_descripcion),
            ('Lengua', self.examen_lengua, self.examen_lengua_descripcion),
            ('Paladar', self.examen_paladar, self.examen_paladar_descripcion),
            ('Piso de la boca', self.examen_piso_boca, self.examen_piso_boca_descripcion),
            ('Carrillos', self.examen_carrillos, self.examen_carrillos_descripcion),
            ('Región 9', self.examen_region_9, self.examen_region_9_descripcion),
            ('Glándulas salivales', self.examen_glandulas_salivales, self.examen_glandulas_salivales_descripcion),
            ('Orofaringe', self.examen_oro_faringe, self.examen_oro_faringe_descripcion),
            ('A.T.M.', self.examen_atm, self.examen_atm_descripcion),
            ('Ganglios', self.examen_ganglios, self.examen_ganglios_descripcion),
        ]
        
        for nombre, estado, descripcion in campos_examen:
            if estado == 'ANORMAL':
                areas_anormales.append({
                    'area': nombre,
                    'descripcion': descripcion
                })
        
        return areas_anormales