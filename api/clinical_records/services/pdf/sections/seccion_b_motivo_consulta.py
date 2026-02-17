# api/clinical_records/services/pdf/sections/seccion_b_motivo_consulta.py
"""
Sección B del Formulario 033: MOTIVO DE CONSULTA

Estructura:
  - MOTIVO DE CONSULTA (campo de texto amplio)
  - EMBARAZADA (SI / NO) - en la misma fila (solo visible para pacientes femeninos)

Diseño: UI compacta con texto ocupando espacio según necesite
"""
from typing import List, Optional

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
GRIS_CLARO = colors.HexColor('#F5F5F5')


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

def _estilo_valor_embarazada():
    """Valor del campo embarazada con formato especial."""
    return ParagraphStyle(
        'ValorCampoEmbarazada',
        fontSize=10,
        fontName='Helvetica-Bold',
        textColor=VERDE_OSCURO,
        leading=13,
        alignment=TA_CENTER,
    )

def _estilo_no_aplica():
    """Estilo para campos que no aplican."""
    return ParagraphStyle(
        'NoAplica',
        fontSize=8,
        fontName='Helvetica-Oblique',
        textColor=GRIS_ETIQUETA,
        leading=10,
        alignment=TA_CENTER,
    )

def _estilo_titulo_seccion():
    """Título de la sección."""
    return ParagraphStyle(
        'TituloSeccionB',
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=BLANCO,
        alignment=TA_CENTER,
        leading=13,
    )


# ═══════════════════════════════════════════════════════════════════════════
# CLASE PRINCIPAL - SECCIÓN B
# ═══════════════════════════════════════════════════════════════════════════
class SeccionBMotivoConsulta(BaseSeccion):
    """
    Sección B del Formulario 033: MOTIVO DE CONSULTA
    
    Muestra el motivo de consulta del paciente.
    El campo EMBARAZADA solo se muestra para pacientes femeninos.
    """
    
    @property
    def nombre_seccion(self) -> str:
        return 'B. Motivo de Consulta'
    
    @property
    def es_opcional(self) -> bool:
        return False  # Siempre debe aparecer
    
    def construir(self, historial) -> List[Flowable]:
        """
        Construye la sección B.
        
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
                'B. MOTIVO DE CONSULTA',
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
        # CONTENIDO: MOTIVO + EMBARAZADA (solo si aplica)
        # ═══════════════════════════════════════════════════════════════════
        
        # Obtener valores
        motivo_consulta = historial.motivo_consulta or '—'
        embarazada = historial.embarazada or 'NO'
        sexo_paciente = historial.paciente.sexo if historial.paciente else None
        
        # Determinar si mostrar campo embarazada
        mostrar_embarazada = sexo_paciente == 'F'  # Solo para mujeres
        
        # Anchos de columna
        if mostrar_embarazada:
            w_motivo = 130 * mm  # Ancho normal cuando está embarazada
            w_embarazada = 40 * mm
            col_widths = [w_motivo, w_embarazada]
            celdas = [
                self._crear_celda_motivo(motivo_consulta, w_motivo),
                self._crear_celda_embarazada(embarazada, w_embarazada)
            ]
        else:
            # Sin campo embarazada - motivo ocupa todo el ancho
            w_motivo = 170 * mm  # Ancho completo
            col_widths = [w_motivo]
            celdas = [self._crear_celda_motivo(motivo_consulta, w_motivo, ocultar_embarazada=True)]
        
        # Tabla con columnas según corresponda
        fila = Table(
            [celdas],
            colWidths=col_widths,
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
    
    def _crear_celda_motivo(self, motivo: str, ancho: float, ocultar_embarazada: bool = False) -> Table:
        """
        Crea la celda del motivo de consulta.
        
        Args:
            motivo: Texto del motivo de consulta
            ancho: Ancho de la celda
            ocultar_embarazada: Indica si el campo embarazada está oculto
            
        Returns:
            Tabla con la celda formateada
        """
        etiqueta_texto = 'MOTIVO DE CONSULTA'
        if ocultar_embarazada:
            # Si no hay campo embarazada, podemos indicar que no aplica sutilmente
            etiqueta_texto = 'MOTIVO DE CONSULTA'
        
        etiqueta_para = Paragraph(etiqueta_texto, _estilo_etiqueta())
        valor_para = Paragraph(motivo, _estilo_valor())
        
        celda = Table(
            [
                [etiqueta_para],
                [valor_para],
            ],
            colWidths=[ancho],
        )
        
        style = [
            ('BACKGROUND', (0, 0), (-1, 0), VERDE_MUY_CLARO),
            ('BACKGROUND', (0, 1), (-1, 1), BLANCO),
            ('BOX', (0, 0), (-1, -1), 0.5, VERDE_CLARO),
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, VERDE_CLARO),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]
        
        celda.setStyle(TableStyle(style))
        
        return celda
    
    def _crear_celda_embarazada(self, embarazada: str, ancho: float) -> Table:
        """
        Crea la celda del campo EMBARAZADA.
        
        Args:
            embarazada: 'SI', 'NO' o None
            ancho: Ancho de la celda
            
        Returns:
            Tabla con la celda formateada
        """
        # Normalizar valor
        embarazada_valor = str(embarazada).upper() if embarazada else 'NO'
        
        etiqueta_para = Paragraph('EMBARAZADA', _estilo_etiqueta())
        
        # Mostrar el valor de forma más visual
        if embarazada_valor == 'SI':
            valor_html = f"""
            <font size="10" color="#27AE60"><b> SI</b></font>
            """
            fondo_color = VERDE_MUY_CLARO
        else:
            valor_html = f"""
            <font size="10" color="#E74C3C"><b> NO</b></font>
            """
            fondo_color = GRIS_CLARO
        
        valor_para = Paragraph(valor_html, _estilo_valor_embarazada())
        
        celda = Table(
            [
                [etiqueta_para],
                [valor_para],
            ],
            colWidths=[ancho],
        )
        
        celda.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), VERDE_MUY_CLARO),
            ('BACKGROUND', (0, 1), (-1, 1), fondo_color),
            ('BOX', (0, 0), (-1, 0), 0, VERDE_CLARO),
            ('LINEBELOW', (0, 0), (-1, 0), 0, VERDE_CLARO),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
        ]))
        
        return celda


# ═══════════════════════════════════════════════════════════════════════════
# EXPORTACIÓN
# ═══════════════════════════════════════════════════════════════════════════
__all__ = ['SeccionBMotivoConsulta']