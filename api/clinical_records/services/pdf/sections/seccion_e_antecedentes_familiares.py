# api/clinical_records/services/pdf/sections/seccion_e_antecedentes_familiares.py
"""
Sección E del Formulario 033: ANTECEDENTES PATOLÓGICOS FAMILIARES

Estructura:
  - Lista de antecedentes familiares del paciente
  - Enfermedades hereditarias
  - Relación con el paciente

Diseño: Tabla con datos estructurados
"""
from typing import List

from reportlab.platypus import Flowable, Table, TableStyle, Spacer, Paragraph
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER

from .base_section import (
    BaseSeccion, 
    ANCHO_PAGINA, 
    ESTILOS,
    COLOR_PRIMARIO, 
    COLOR_SECUNDARIO,
    COLOR_BORDE,
    COLOR_ACENTO,
)


# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════
VERDE_OSCURO = COLOR_PRIMARIO
VERDE_MEDIO = COLOR_SECUNDARIO
VERDE_CLARO = COLOR_BORDE
VERDE_MUY_CLARO = COLOR_ACENTO
GRIS_TEXTO = colors.HexColor('#2C3E50')
GRIS_ETIQUETA = colors.HexColor('#5D6D7E')
BLANCO = colors.white


# ═══════════════════════════════════════════════════════════════════════════
# ESTILOS DE TEXTO
# ═══════════════════════════════════════════════════════════════════════════
def _estilo_etiqueta():
    """Etiqueta de campo."""
    return ParagraphStyle(
        'EtiquetaCampo',
        fontSize=8,
        fontName='Helvetica-Bold',
        textColor=GRIS_ETIQUETA,
        leading=10,
        alignment=TA_LEFT,
    )

def _estilo_valor():
    """Valor del campo."""
    return ParagraphStyle(
        'ValorCampo',
        fontSize=9,
        fontName='Helvetica',
        textColor=GRIS_TEXTO,
        leading=11,
        alignment=TA_LEFT,
    )

def _estilo_titulo_seccion():
    """Título de la sección."""
    return ParagraphStyle(
        'TituloSeccionE',
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=BLANCO,
        alignment=TA_CENTER,
        leading=13,
    )


# ═══════════════════════════════════════════════════════════════════════════
# CLASE PRINCIPAL - SECCIÓN E
# ═══════════════════════════════════════════════════════════════════════════
class SeccionEAntecedentesFamiliares(BaseSeccion):
    """
    Sección E del Formulario 033: ANTECEDENTES PATOLÓGICOS FAMILIARES
    
    Muestra los antecedentes médicos familiares del paciente incluyendo
    enfermedades hereditarias y parentesco.
    """
    
    @property
    def nombre_seccion(self) -> str:
        return 'E. Antecedentes Patológicos Familiares'
    
    @property
    def es_opcional(self) -> bool:
        return False  # Siempre debe aparecer
    
    def construir(self, historial) -> List[Flowable]:
        """
        Construye la sección E.
        
        Args:
            historial: Instancia de ClinicalRecord
            
        Returns:
            Lista de elementos Flowable
        """
        elementos = []
        
        # ═══════════════════════════════════════════════════════════════════
        # ENCABEZADO
        # ═══════════════════════════════════════════════════════════════════
        titulo = Table(
            [[Paragraph(
                'E. ANTECEDENTES PATOLÓGICOS FAMILIARES',
                _estilo_titulo_seccion()
            )]],
            colWidths=[ANCHO_PAGINA],
        )
        titulo.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), VERDE_OSCURO),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elementos.append(titulo)
        elementos.append(Spacer(1, 2))
        
        # ═══════════════════════════════════════════════════════════════════
        # CONTENIDO
        # ═══════════════════════════════════════════════════════════════════
        
        # Obtener antecedentes
        antecedentes = historial.antecedentes_familiares
        
        if not antecedentes:
            # Sin datos
            elementos.extend(self.sin_datos())
        else:
            # Construir tabla con datos
            elementos.extend(self._construir_tabla_antecedentes(antecedentes))
        
        elementos.append(Spacer(1, 8))
        
        return elementos
    
    def _construir_tabla_antecedentes(self, antecedentes) -> List[Flowable]:
        """
        Construye la tabla con los antecedentes familiares.
        Usa los campos reales del modelo AntecedentesFamiliares.
        """
        elementos = []

        # Cada tupla: (etiqueta, campo_principal, campo_otro, metodo_display, valor_negativo)
        campos = [
            ('Cardiopatía',              'cardiopatia_familiar',           'cardiopatia_familiar_otro',           'get_cardiopatia_familiar_display',           'NO'),
            ('Hipertensión Arterial',    'hipertension_arterial_familiar', 'hipertension_arterial_familiar_otro', 'get_hipertension_arterial_familiar_display', 'NO'),
            ('Enfermedad Vascular',      'enfermedad_vascular_familiar',   'enfermedad_vascular_familiar_otro',   'get_enfermedad_vascular_familiar_display',   'NO'),
            ('Endócrino Metabólico',     'endocrino_metabolico_familiar',  'endocrino_metabolico_familiar_otro',  'get_endocrino_metabolico_familiar_display',  'NO'),
            ('Cáncer',                   'cancer_familiar',                'cancer_familiar_otro',                'get_cancer_familiar_display',                'NO'),
            ('Tuberculosis',             'tuberculosis_familiar',           'tuberculosis_familiar_otro',           'get_tuberculosis_familiar_display',           'NO'),
            ('Enfermedad Mental',        'enfermedad_mental_familiar',     'enfermedad_mental_familiar_otro',     'get_enfermedad_mental_familiar_display',     'NO'),
            ('Enfermedad Infecciosa',    'enfermedad_infecciosa_familiar', 'enfermedad_infecciosa_familiar_otro', 'get_enfermedad_infecciosa_familiar_display', 'NO'),
            ('Malformación',             'malformacion_familiar',          'malformacion_familiar_otro',          'get_malformacion_familiar_display',          'NO'),
        ]

        for etiqueta, campo, campo_otro, metodo_display, neg in campos:
            valor = self._display_con_detalle(antecedentes, campo, campo_otro, metodo_display, neg)

            # Para cáncer, agregar tipo si aplica
            if campo == 'cancer_familiar' and getattr(antecedentes, 'cancer_familiar', 'NO') != 'NO':
                tipo_cancer = getattr(antecedentes, 'tipo_cancer', '')
                tipo_otro   = getattr(antecedentes, 'tipo_cancer_otro', '')
                metodo_tipo = getattr(antecedentes, 'get_tipo_cancer_display', None)
                if tipo_cancer:
                    tipo_txt = metodo_tipo() if callable(metodo_tipo) else tipo_cancer
                    if tipo_cancer == 'OTRO' and tipo_otro:
                        tipo_txt = tipo_otro
                    valor += f' — Tipo: {tipo_txt}'

            elementos.append(self._crear_fila_dato(etiqueta, valor))

        # Otros antecedentes (texto libre)
        otros = getattr(antecedentes, 'otros_antecedentes_familiares', '') or '—'
        elementos.append(self._crear_fila_dato('Otros Antecedentes', otros))

        return elementos

    def _display_con_detalle(self, obj, campo, campo_otro, metodo_display, valor_negativo) -> str:
        """
        Devuelve el display legible de un campo choice + su detalle '_otro'.
        Si el valor es igual a valor_negativo retorna 'No'.
        """
        valor = getattr(obj, campo, valor_negativo)
        if valor == valor_negativo:
            return 'No'
        metodo = getattr(obj, metodo_display, None)
        texto = metodo() if callable(metodo) else str(valor)
        detalle = getattr(obj, campo_otro, '') or ''
        if detalle:
            texto += f' — {detalle}'
        return texto
    
    def _crear_fila_dato(self, etiqueta: str, valor: str) -> Table:
        """
        Crea una fila con etiqueta y valor.
        
        Args:
            etiqueta: Etiqueta del campo
            valor: Valor del campo
            
        Returns:
            Tabla con la fila formateada
        """
        etiqueta_para = Paragraph(etiqueta.upper(), _estilo_etiqueta())
        valor_para = Paragraph(valor, _estilo_valor())
        
        tabla = Table(
            [[etiqueta_para, valor_para]],
            colWidths=[60 * mm, 110 * mm],
        )
        
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), VERDE_MUY_CLARO),
            ('BACKGROUND', (1, 0), (1, 0), BLANCO),
            ('BOX', (0, 0), (-1, -1), 0.5, VERDE_CLARO),
            ('LINEAFTER', (0, 0), (0, 0), 0.5, VERDE_CLARO),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        return tabla
    



# ═══════════════════════════════════════════════════════════════════════════
# EXPORTACIÓN
# ═══════════════════════════════════════════════════════════════════════════
__all__ = ['SeccionEAntecedentesFamiliares']