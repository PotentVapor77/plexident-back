# api/clinical_records/services/pdf/sections/seccion_c_enfermedad_actual.py
"""
Sección C del Formulario 033: ENFERMEDAD ACTUAL

Estructura:
  - ENFERMEDAD ACTUAL (campo de texto amplio que ocupa toda la fila)

Diseño: UI simple con espacio flexible según contenido
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
        fontSize=7,
        fontName='Helvetica-Bold',
        textColor=GRIS_ETIQUETA,
        leading=9,
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
        'TituloSeccionC',
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=BLANCO,
        alignment=TA_CENTER,
        leading=13,
    )


# ═══════════════════════════════════════════════════════════════════════════
# CLASE PRINCIPAL - SECCIÓN C
# ═══════════════════════════════════════════════════════════════════════════
class SeccionCEnfermedadActual(BaseSeccion):
    """
    Sección C del Formulario 033: ENFERMEDAD ACTUAL
    
    Muestra la descripción de la enfermedad actual del paciente
    en una fila que se expande según el contenido.
    """
    
    @property
    def nombre_seccion(self) -> str:
        return 'C. Enfermedad Actual'
    
    @property
    def es_opcional(self) -> bool:
        return False  # Siempre debe aparecer
    
    def construir(self, historial) -> List[Flowable]:
        """
        Construye la sección C.
        
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
                'C. ENFERMEDAD ACTUAL',
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
        # CONTENIDO: ENFERMEDAD ACTUAL
        # ═══════════════════════════════════════════════════════════════════
        
        # Obtener valor
        # Intentar obtener de constantes vitales primero
        enfermedad_actual = '—'
        
        if historial.constantes_vitales and hasattr(historial.constantes_vitales, 'enfermedad_actual'):
            enfermedad_actual = historial.constantes_vitales.enfermedad_actual or '—'
        elif hasattr(historial, 'enfermedad_actual'):
            enfermedad_actual = historial.enfermedad_actual or '—'
        
        # Crear celda
        celda = self._crear_celda_enfermedad(enfermedad_actual, ANCHO_PAGINA)
        
        elementos.append(celda)
        elementos.append(Spacer(1, 8))
        
        return elementos
    
    def _crear_celda_enfermedad(self, enfermedad: str, ancho: float) -> Table:
        """
        Crea la celda de enfermedad actual.
        
        Args:
            enfermedad: Texto de la enfermedad actual
            ancho: Ancho de la celda
            
        Returns:
            Tabla con la celda formateada
        """
        etiqueta_para = Paragraph('ENFERMEDAD ACTUAL', _estilo_etiqueta())
        valor_para = Paragraph(enfermedad, _estilo_valor())
        
        celda = Table(
            [
                [etiqueta_para],
                [valor_para],
            ],
            colWidths=[ancho],
        )
        
        celda.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), VERDE_MUY_CLARO),
            ('BACKGROUND', (0, 1), (-1, 1), BLANCO),
            ('BOX', (0, 0), (-1, -1), 0.5, VERDE_CLARO),
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, VERDE_CLARO),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        return celda


# ═══════════════════════════════════════════════════════════════════════════
# EXPORTACIÓN
# ═══════════════════════════════════════════════════════════════════════════
__all__ = ['SeccionCEnfermedadActual']