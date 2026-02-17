# api/clinical_records/services/pdf/sections/seccion_f_constantes_vitales.py
"""
Sección F del Formulario 033: CONSTANTES VITALES

Estructura:
  - TEMPERATURA °C
  - PULSO / min
  - FRECUENCIA RESPIRATORIA / min
  - PRESIÓN ARTERIAL (mmHg)
  
Todo en una sola fila compacta.

Diseño: UI compacta con 4 columnas
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
        fontSize=6,
        fontName='Helvetica-Bold',
        textColor=GRIS_ETIQUETA,
        leading=8,
        alignment=TA_CENTER,
    )

def _estilo_valor():
    """Valor del campo."""
    return ParagraphStyle(
        'ValorCampo',
        fontSize=10,
        fontName='Helvetica-Bold',
        textColor=GRIS_TEXTO,
        leading=12,
        alignment=TA_CENTER,
    )

def _estilo_titulo_seccion():
    """Título de la sección."""
    return ParagraphStyle(
        'TituloSeccionF',
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=BLANCO,
        alignment=TA_CENTER,
        leading=13,
    )


# ═══════════════════════════════════════════════════════════════════════════
# CLASE PRINCIPAL - SECCIÓN F
# ═══════════════════════════════════════════════════════════════════════════
class SeccionFConstantesVitales(BaseSeccion):
    """
    Sección F del Formulario 033: CONSTANTES VITALES
    
    Muestra las constantes vitales del paciente en una fila compacta.
    """
    
    @property
    def nombre_seccion(self) -> str:
        return 'F. Constantes Vitales'
    
    @property
    def es_opcional(self) -> bool:
        return False  # Siempre debe aparecer
    
    def construir(self, historial) -> List[Flowable]:
        """
        Construye la sección F.
        
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
                'F. CONSTANTES VITALES',
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
        # CONTENIDO: 4 COLUMNAS
        # ═══════════════════════════════════════════════════════════════════
        
        # Obtener valores
        constantes = historial.constantes_vitales
        
        if constantes:
            temperatura = f"{constantes.temperatura} °C" if constantes.temperatura else '—'
            pulso = f"{constantes.pulso} /min" if constantes.pulso else '—'
            freq_resp = f"{constantes.frecuencia_respiratoria} /min" if constantes.frecuencia_respiratoria else '—'
            presion = constantes.presion_arterial or '—'
        else:
            temperatura = '—'
            pulso = '—'
            freq_resp = '—'
            presion = '—'
        
        # Anchos de columna (4 columnas iguales)
        w_columna = ANCHO_PAGINA / 4
        
        # Crear celdas
        celda_temp = self._crear_celda('TEMPERATURA<br/>°C', temperatura, w_columna)
        celda_pulso = self._crear_celda('PULSO<br/>/min', pulso, w_columna)
        celda_freq = self._crear_celda('FRECUENCIA<br/>RESPIRATORIA<br/>/min', freq_resp, w_columna)
        celda_presion = self._crear_celda('PRESIÓN<br/>ARTERIAL<br/>(mmHg)', presion, w_columna)
        
        # Tabla con 4 columnas
        fila = Table(
            [[celda_temp, celda_pulso, celda_freq, celda_presion]],
            colWidths=[w_columna, w_columna, w_columna, w_columna],
        )
        
        fila.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        elementos.append(fila)
        elementos.append(Spacer(1, 8))
        
        return elementos
    
    def _crear_celda(self, etiqueta: str, valor: str, ancho: float) -> Table:
        """
        Crea una celda individual para una constante vital.
        
        Args:
            etiqueta: Etiqueta del campo (puede tener <br/> para saltos)
            valor: Valor del campo
            ancho: Ancho de la celda
            
        Returns:
            Tabla con la celda formateada
        """
        etiqueta_para = Paragraph(etiqueta, _estilo_etiqueta())
        valor_para = Paragraph(valor, _estilo_valor())
        
        celda = Table(
            [
                [etiqueta_para],
                [valor_para],
            ],
            colWidths=[ancho],
            rowHeights=[12 * mm, 10 * mm],  # Altura fija para uniformidad
        )
        
        celda.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), VERDE_MUY_CLARO),
            ('BACKGROUND', (0, 1), (-1, 1), BLANCO),
            ('BOX', (0, 0), (-1, -1), 0.5, VERDE_CLARO),
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, VERDE_CLARO),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        
        return celda


# ═══════════════════════════════════════════════════════════════════════════
# EXPORTACIÓN
# ═══════════════════════════════════════════════════════════════════════════
__all__ = ['SeccionFConstantesVitales']