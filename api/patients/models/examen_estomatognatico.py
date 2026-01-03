# patients/models/examen_estomatognatico.py
from django.db import models
from django.core.exceptions import ValidationError
from .base import BaseModel
from .paciente import Paciente


class ExamenEstomatognatico(BaseModel):
    """Examen del sistema estomatognático (Sección G)"""
    
    paciente = models.OneToOneField(
        Paciente,
        on_delete=models.CASCADE,
        related_name='examen_estomatognatico',
        verbose_name="Paciente"
    )
    
    # Checkbox general
    examen_sin_patologia = models.BooleanField(
        default=False,
        verbose_name="Examen sin patología",
        help_text="Marcar si todo el examen está normal"
    )
    
    # ARTICULACIÓN TÉMPORO-MANDIBULAR (ATM) - Sección especial
    atm_cp = models.BooleanField(default=False, verbose_name="ATM - Con Patología")
    atm_sp = models.BooleanField(default=False, verbose_name="ATM - Sin Patología")
    atm_absceso = models.BooleanField(default=False, verbose_name="Absceso")
    atm_fibroma = models.BooleanField(default=False, verbose_name="Fibroma")
    atm_herpes = models.BooleanField(default=False, verbose_name="Herpes")
    atm_ulcera = models.BooleanField(default=False, verbose_name="Úlcera")
    atm_otra_patologia = models.BooleanField(default=False, verbose_name="Otra patología")
    atm_observacion = models.TextField(blank=True, verbose_name="Observación ATM")
    
    # 1. MEJILLAS
    mejillas_cp = models.BooleanField(default=False, verbose_name="Mejillas - CP")
    mejillas_sp = models.BooleanField(default=False, verbose_name="Mejillas - SP")
    mejillas_absceso = models.BooleanField(default=False, verbose_name="Mejillas - Absceso")
    mejillas_fibroma = models.BooleanField(default=False, verbose_name="Mejillas - Fibroma")
    mejillas_herpes = models.BooleanField(default=False, verbose_name="Mejillas - Herpes")
    mejillas_ulcera = models.BooleanField(default=False, verbose_name="Mejillas - Úlcera")
    mejillas_otra_patologia = models.BooleanField(default=False, verbose_name="Mejillas - Otra patología")
    mejillas_descripcion = models.TextField(blank=True, verbose_name="Descripción mejillas")
    
    # 2. MAXILAR INFERIOR
    maxilar_inferior_cp = models.BooleanField(default=False, verbose_name="Maxilar Inferior - CP")
    maxilar_inferior_sp = models.BooleanField(default=False, verbose_name="Maxilar Inferior - SP")
    maxilar_inferior_absceso = models.BooleanField(default=False, verbose_name="Maxilar Inferior - Absceso")
    maxilar_inferior_fibroma = models.BooleanField(default=False, verbose_name="Maxilar Inferior - Fibroma")
    maxilar_inferior_herpes = models.BooleanField(default=False, verbose_name="Maxilar Inferior - Herpes")
    maxilar_inferior_ulcera = models.BooleanField(default=False, verbose_name="Maxilar Inferior - Úlcera")
    maxilar_inferior_otra_patologia = models.BooleanField(default=False, verbose_name="Maxilar Inferior - Otra patología")
    maxilar_inferior_descripcion = models.TextField(blank=True, verbose_name="Descripción maxilar inferior")
    
    # 3. MAXILAR SUPERIOR
    maxilar_superior_cp = models.BooleanField(default=False, verbose_name="Maxilar Superior - CP")
    maxilar_superior_sp = models.BooleanField(default=False, verbose_name="Maxilar Superior - SP")
    maxilar_superior_absceso = models.BooleanField(default=False, verbose_name="Maxilar Superior - Absceso")
    maxilar_superior_fibroma = models.BooleanField(default=False, verbose_name="Maxilar Superior - Fibroma")
    maxilar_superior_herpes = models.BooleanField(default=False, verbose_name="Maxilar Superior - Herpes")
    maxilar_superior_ulcera = models.BooleanField(default=False, verbose_name="Maxilar Superior - Úlcera")
    maxilar_superior_otra_patologia = models.BooleanField(default=False, verbose_name="Maxilar Superior - Otra patología")
    maxilar_superior_descripcion = models.TextField(blank=True, verbose_name="Descripción maxilar superior")
    
    # 4. PALADAR
    paladar_cp = models.BooleanField(default=False, verbose_name="Paladar - CP")
    paladar_sp = models.BooleanField(default=False, verbose_name="Paladar - SP")
    paladar_absceso = models.BooleanField(default=False, verbose_name="Paladar - Absceso")
    paladar_fibroma = models.BooleanField(default=False, verbose_name="Paladar - Fibroma")
    paladar_herpes = models.BooleanField(default=False, verbose_name="Paladar - Herpes")
    paladar_ulcera = models.BooleanField(default=False, verbose_name="Paladar - Úlcera")
    paladar_otra_patologia = models.BooleanField(default=False, verbose_name="Paladar - Otra patología")
    paladar_descripcion = models.TextField(blank=True, verbose_name="Descripción paladar")
    
    # 5. PISO DE BOCA
    piso_boca_cp = models.BooleanField(default=False, verbose_name="Piso de Boca - CP")
    piso_boca_sp = models.BooleanField(default=False, verbose_name="Piso de Boca - SP")
    piso_boca_absceso = models.BooleanField(default=False, verbose_name="Piso de Boca - Absceso")
    piso_boca_fibroma = models.BooleanField(default=False, verbose_name="Piso de Boca - Fibroma")
    piso_boca_herpes = models.BooleanField(default=False, verbose_name="Piso de Boca - Herpes")
    piso_boca_ulcera = models.BooleanField(default=False, verbose_name="Piso de Boca - Úlcera")
    piso_boca_otra_patologia = models.BooleanField(default=False, verbose_name="Piso de Boca - Otra patología")
    piso_boca_descripcion = models.TextField(blank=True, verbose_name="Descripción piso de boca")
    
    # 6. CARRILLOS
    carrillos_cp = models.BooleanField(default=False, verbose_name="Carrillos - CP")
    carrillos_sp = models.BooleanField(default=False, verbose_name="Carrillos - SP")
    carrillos_absceso = models.BooleanField(default=False, verbose_name="Carrillos - Absceso")
    carrillos_fibroma = models.BooleanField(default=False, verbose_name="Carrillos - Fibroma")
    carrillos_herpes = models.BooleanField(default=False, verbose_name="Carrillos - Herpes")
    carrillos_ulcera = models.BooleanField(default=False, verbose_name="Carrillos - Úlcera")
    carrillos_otra_patologia = models.BooleanField(default=False, verbose_name="Carrillos - Otra patología")
    carrillos_descripcion = models.TextField(blank=True, verbose_name="Descripción carrillos")
    
    # 7. GLÁNDULAS SALIVALES
    glandulas_salivales_cp = models.BooleanField(default=False, verbose_name="Glándulas Salivales - CP")
    glandulas_salivales_sp = models.BooleanField(default=False, verbose_name="Glándulas Salivales - SP")
    glandulas_salivales_absceso = models.BooleanField(default=False, verbose_name="Glándulas Salivales - Absceso")
    glandulas_salivales_fibroma = models.BooleanField(default=False, verbose_name="Glándulas Salivales - Fibroma")
    glandulas_salivales_herpes = models.BooleanField(default=False, verbose_name="Glándulas Salivales - Herpes")
    glandulas_salivales_ulcera = models.BooleanField(default=False, verbose_name="Glándulas Salivales - Úlcera")
    glandulas_salivales_otra_patologia = models.BooleanField(default=False, verbose_name="Glándulas Salivales - Otra patología")
    glandulas_salivales_descripcion = models.TextField(blank=True, verbose_name="Descripción glándulas salivales")
    
    # 8. GANGLIOS DE CABEZA Y CUELLO
    ganglios_cp = models.BooleanField(default=False, verbose_name="Ganglios - CP")
    ganglios_sp = models.BooleanField(default=False, verbose_name="Ganglios - SP")
    ganglios_absceso = models.BooleanField(default=False, verbose_name="Ganglios - Absceso")
    ganglios_fibroma = models.BooleanField(default=False, verbose_name="Ganglios - Fibroma")
    ganglios_herpes = models.BooleanField(default=False, verbose_name="Ganglios - Herpes")
    ganglios_ulcera = models.BooleanField(default=False, verbose_name="Ganglios - Úlcera")
    ganglios_otra_patologia = models.BooleanField(default=False, verbose_name="Ganglios - Otra patología")
    ganglios_descripcion = models.TextField(blank=True, verbose_name="Descripción ganglios")
    
    # 9. LENGUA
    lengua_cp = models.BooleanField(default=False, verbose_name="Lengua - CP")
    lengua_sp = models.BooleanField(default=False, verbose_name="Lengua - SP")
    lengua_absceso = models.BooleanField(default=False, verbose_name="Lengua - Absceso")
    lengua_fibroma = models.BooleanField(default=False, verbose_name="Lengua - Fibroma")
    lengua_herpes = models.BooleanField(default=False, verbose_name="Lengua - Herpes")
    lengua_ulcera = models.BooleanField(default=False, verbose_name="Lengua - Úlcera")
    lengua_otra_patologia = models.BooleanField(default=False, verbose_name="Lengua - Otra patología")
    lengua_descripcion = models.TextField(blank=True, verbose_name="Descripción lengua")
    
    # 10. LABIOS
    labios_cp = models.BooleanField(default=False, verbose_name="Labios - CP")
    labios_sp = models.BooleanField(default=False, verbose_name="Labios - SP")
    labios_absceso = models.BooleanField(default=False, verbose_name="Labios - Absceso")
    labios_fibroma = models.BooleanField(default=False, verbose_name="Labios - Fibroma")
    labios_herpes = models.BooleanField(default=False, verbose_name="Labios - Herpes")
    labios_ulcera = models.BooleanField(default=False, verbose_name="Labios - Úlcera")
    labios_otra_patologia = models.BooleanField(default=False, verbose_name="Labios - Otra patología")
    labios_descripcion = models.TextField(blank=True, verbose_name="Descripción labios")
    
    class Meta:
        verbose_name = "Examen Estomatognático"
        verbose_name_plural = "Exámenes Estomatognáticos"
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"Examen estomatognático de {self.paciente.nombre_completo}"
    
    def clean(self):
        """Validación personalizada"""
        super().clean()
        
        # Validar que no se marquen ambos CP y SP para la misma región
        regiones = [
            ('mejillas', self.mejillas_cp, self.mejillas_sp),
            ('maxilar_inferior', self.maxilar_inferior_cp, self.maxilar_inferior_sp),
            ('maxilar_superior', self.maxilar_superior_cp, self.maxilar_superior_sp),
            ('paladar', self.paladar_cp, self.paladar_sp),
            ('piso_boca', self.piso_boca_cp, self.piso_boca_sp),
            ('carrillos', self.carrillos_cp, self.carrillos_sp),
            ('glandulas_salivales', self.glandulas_salivales_cp, self.glandulas_salivales_sp),
            ('ganglios', self.ganglios_cp, self.ganglios_sp),
            ('lengua', self.lengua_cp, self.lengua_sp),
            ('labios', self.labios_cp, self.labios_sp),
            ('atm', self.atm_cp, self.atm_sp),
        ]
        
        for nombre, cp, sp in regiones:
            if cp and sp:
                raise ValidationError(f"No se puede marcar CP y SP simultáneamente para {nombre}")
    
    @property
    def regiones_con_patologia(self):
        """Retorna lista de regiones con patología"""
        regiones = []
        
        campos = [
            ('Mejillas', self.mejillas_cp, self.mejillas_descripcion),
            ('Maxilar Inferior', self.maxilar_inferior_cp, self.maxilar_inferior_descripcion),
            ('Maxilar Superior', self.maxilar_superior_cp, self.maxilar_superior_descripcion),
            ('Paladar', self.paladar_cp, self.paladar_descripcion),
            ('Piso de Boca', self.piso_boca_cp, self.piso_boca_descripcion),
            ('Carrillos', self.carrillos_cp, self.carrillos_descripcion),
            ('Glándulas Salivales', self.glandulas_salivales_cp, self.glandulas_salivales_descripcion),
            ('Ganglios', self.ganglios_cp, self.ganglios_descripcion),
            ('Lengua', self.lengua_cp, self.lengua_descripcion),
            ('Labios', self.labios_cp, self.labios_descripcion),
        ]
        
        for nombre, tiene_patologia, descripcion in campos:
            if tiene_patologia:
                regiones.append({
                    'region': nombre,
                    'descripcion': descripcion
                })
        
        return regiones
    
    @property
    def atm_patologias(self):
        """Retorna diccionario con patologías de ATM detectadas"""
        return {
            'absceso': self.atm_absceso,
            'fibroma': self.atm_fibroma,
            'herpes': self.atm_herpes,
            'ulcera': self.atm_ulcera,
            'otra': self.atm_otra_patologia,
            'observacion': self.atm_observacion
        }
    
    @property
    def tiene_patologias(self):
        """Verifica si hay alguna patología registrada"""
        return (
            not self.examen_sin_patologia and 
            any([
                self.mejillas_cp, self.maxilar_inferior_cp, self.maxilar_superior_cp,
                self.paladar_cp, self.piso_boca_cp, self.carrillos_cp,
                self.glandulas_salivales_cp, self.ganglios_cp, self.lengua_cp,
                self.labios_cp, self.atm_cp
            ])
        )