# api/clinical_records/services/pdf/sections/seccion_k_simbologia_odontograma.py
"""
Sección K del Formulario 033: SIMBOLOGÍA DEL ODONTOGRAMA

Muestra la leyenda completa de símbolos utilizados en el odontograma,
adaptada para coincidir con la implementación del frontend React.
"""

from typing import List, Dict, Tuple, Optional

from reportlab.platypus import Flowable, Table, TableStyle, Spacer, Paragraph
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.utils import ImageReader

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
VERDE_OSCURO = COLOR_PRIMARIO  # #2E7D32
VERDE_MEDIO = COLOR_SECUNDARIO  # #81C784
VERDE_CLARO = COLOR_BORDE  # #A5D6A7
VERDE_MUY_CLARO = COLOR_ACENTO  # #EDF2F7
GRIS_TEXTO = colors.HexColor('#2C3E50')
GRIS_ETIQUETA = colors.HexColor('#5D6D7E')
BLANCO = colors.white

# Colores específicos del odontograma (coincidiendo con frontend)
C_ROJO = "#FF0000"          # Rojo para indicado/por realizar
C_AZUL = "#0000FF"          # Azul para realizado
C_VERDE = "#00AA00"          # Verde para sano
C_NEGRO = "#000000"          # Negro para ausente

# Símbolos del odontograma según frontend React
SIMBOLOS_FRONTEND: List[Dict[str, str]] = [
    {"simbolo": "O", "color": C_ROJO, "desc": "Caries en superficies"},
    {"simbolo": "O", "color": C_AZUL, "desc": "Obturado en superficies"},
    {"simbolo": "A", "color": C_NEGRO, "desc": "Ausente"},
    {"simbolo": "X", "color": C_ROJO, "desc": "Extracción Indicada"},
    {"simbolo": "X", "color": C_AZUL, "desc": "Pérdida por caries"},
    {"simbolo": "ⓧ", "color": C_AZUL, "desc": "Pérdida (otra causa)"},
    {"simbolo": "Ü", "color": C_ROJO, "desc": "Sellante Necesario"},
    {"simbolo": "Ü", "color": C_AZUL, "desc": "Sellante Realizado"},
    {"simbolo": "r", "color": C_ROJO, "desc": "Endodoncia Por Realizar"},
    {"simbolo": "|", "color": C_AZUL, "desc": "Endodoncia Realizada"},
    {"simbolo": "|", "color": C_ROJO, "desc": "Extraccion otra causa"},
    {"simbolo": "¨-¨", "color": C_ROJO, "desc": "Prótesis Fija Indicada"},
    {"simbolo": "¨-¨", "color": C_AZUL, "desc": "Prótesis Fija Realizada"},
    {"simbolo": "(-)", "color": C_ROJO, "desc": "Prótesis Removible Indicada"},
    {"simbolo": "(-)", "color": C_AZUL, "desc": "Prótesis Removible Realizada"},
    {"simbolo": "ª", "color": C_ROJO, "desc": "Corona Indicada"},
    {"simbolo": "ª", "color": C_AZUL, "desc": "Corona Realizada"},
    {"simbolo": "═", "color": C_ROJO, "desc": "Prótesis Total Indicada"},
    {"simbolo": "═", "color": C_AZUL, "desc": "Prótesis Total Realizada"},
    {"simbolo": "✓", "color": C_VERDE, "desc": "Diente Sano"},
]

# Agrupar símbolos por categorías para mejor organización
SIMBOLOS_CATEGORIAS = {
    "Estado del diente": ["A", "✓", "X", "ⓧ"],
    "Caries y obturaciones": ["O"],
    "Endodoncia": ["r", "|"],
    "Prótesis": ["Ü", "¨-¨", "(-)", "ª", "═"],
}


# ═══════════════════════════════════════════════════════════════════════════
# ESTILOS DE TEXTO
# ═══════════════════════════════════════════════════════════════════════════
def _estilo_titulo_seccion():
    """Título de la sección."""
    return ParagraphStyle(
        'TituloSeccionK',
        fontSize=11,
        fontName='Helvetica-Bold',
        textColor=BLANCO,
        alignment=TA_CENTER,
        leading=13,
    )

def _estilo_subtitulo():
    """Subtítulo de la sección."""
    return ParagraphStyle(
        'SubtituloSeccionK',
        fontSize=10,
        fontName='Helvetica-Bold',
        textColor=GRIS_TEXTO,
        alignment=TA_LEFT,
        leading=12,
        spaceAfter=4,
    )

def _estilo_simbolo(color_hex: str):
    """Estilo para el símbolo con color específico."""
    return ParagraphStyle(
        'SimboloK',
        fontSize=12,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor(color_hex),
        alignment=TA_CENTER,
        leading=14,
    )

def _estilo_descripcion():
    """Estilo para la descripción del símbolo."""
    return ParagraphStyle(
        'DescripcionK',
        fontSize=8,
        fontName='Helvetica',
        textColor=GRIS_TEXTO,
        alignment=TA_LEFT,
        leading=10,
    )

def _estilo_nota():
    """Estilo para notas al pie."""
    return ParagraphStyle(
        'NotaK',
        fontSize=7,
        fontName='Helvetica-Oblique',
        textColor=GRIS_ETIQUETA,
        alignment=TA_LEFT,
        leading=9,
    )


# ═══════════════════════════════════════════════════════════════════════════
# CLASE PRINCIPAL - SECCIÓN K
# ═══════════════════════════════════════════════════════════════════════════
class SeccionKSimbologiaOdontograma(BaseSeccion):
    """
    Sección K del Formulario 033: SIMBOLOGÍA DEL ODONTOGRAMA

    Muestra la leyenda completa de símbolos utilizados en el odontograma,
    adaptada para coincidir con la implementación del frontend React.
    """

    @property
    def nombre_seccion(self) -> str:
        return 'K. Simbología del Odontograma'

    @property
    def es_opcional(self) -> bool:
        return True  # Opcional porque es informativa

    def _color_con_opacidad(self, color_hex: str, opacidad: float) -> colors.Color:
        """
        Convierte un color hexadecimal a un objeto Color de ReportLab con opacidad.
        
        Args:
            color_hex: Color en formato hexadecimal (#RRGGBB)
            opacidad: Valor de opacidad entre 0 y 1
            
        Returns:
            Objeto Color de ReportLab con opacidad
        """
        # Eliminar el # si existe
        color_hex = color_hex.lstrip('#')
        
        # Convertir a RGB (valores entre 0 y 1)
        r = int(color_hex[0:2], 16) / 255.0
        g = int(color_hex[2:4], 16) / 255.0
        b = int(color_hex[4:6], 16) / 255.0
        
        # Crear color con opacidad
        return colors.Color(r, g, b, alpha=opacidad)

    def construir(self, historial) -> List[Flowable]:
        """
        Construye la sección K.

        Args:
            historial: Instancia de ClinicalRecord (no se usa directamente)

        Returns:
            Lista de elementos Flowable
        """
        elementos = []

        # ═══════════════════════════════════════════════════════════════════
        # ENCABEZADO
        # ═══════════════════════════════════════════════════════════════════
        titulo = Table(
            [[Paragraph(
                'K. SIMBOLOGÍA DEL ODONTOGRAMA',
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
        elementos.append(Spacer(1, 4))

        # ═══════════════════════════════════════════════════════════════════
        # CONTENIDO - Tabla de símbolos (grid 4 columnas como frontend)
        # ═══════════════════════════════════════════════════════════════════

        # Organizar símbolos en filas de 4 columnas
        filas = []
        for i in range(0, len(SIMBOLOS_FRONTEND), 4):
            fila = []
            for j in range(4):
                if i + j < len(SIMBOLOS_FRONTEND):
                    item = SIMBOLOS_FRONTEND[i + j]
                    fila.append(self._crear_celda_simbolo_frontend(item))
                else:
                    fila.append('')  # Celda vacía para completar
            filas.append(fila)

        # Crear tabla principal con 4 columnas (como frontend)
        ancho_columna = ANCHO_PAGINA / 4
        tabla_simbolos = Table(filas, colWidths=[ancho_columna] * 4)

        tabla_simbolos.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))

        elementos.append(tabla_simbolos)
        elementos.append(Spacer(1, 6))

        # ═══════════════════════════════════════════════════════════════════
        # TABLA DE COLORES DE DIAGNÓSTICO
        # ═══════════════════════════════════════════════════════════════════
        elementos.append(Paragraph("INTERPRETACIÓN DE COLORES", _estilo_subtitulo()))
        elementos.append(self._tabla_colores_diagnostico())
        elementos.append(Spacer(1, 6))

        # ═══════════════════════════════════════════════════════════════════
        # NOTA INFORMATIVA
        # ═══════════════════════════════════════════════════════════════════
        elementos.append(Paragraph(
            "<i>Nota: Rojo = Indicado / Por realizar | Azul = Realizado / Completado | "
            "Verde = Sano | Negro = Ausente</i>",
            _estilo_nota(),
        ))

        elementos.append(Spacer(1, 8))
        return elementos

    def _crear_celda_simbolo_frontend(self, item: Dict[str, str]) -> Table:
        """
        Crea una celda que imita el estilo del frontend React.
        """
        simbolo = item["simbolo"]
        color_hex = item["color"]
        descripcion = item["desc"]
        
        # Calcular anchos
        ancho_total_celda = ANCHO_PAGINA / 4  # Mismo ancho que en la tabla principal
        ancho_simbolo = 8 * mm  # Ancho fijo para el contenedor del símbolo
        ancho_descripcion = ancho_total_celda - ancho_simbolo - 4  # Restando paddings
        
        # Asegurar que el ancho de descripción no sea negativo
        if ancho_descripcion < 10:
            ancho_descripcion = 10
        
        # Color de fondo con 10% de opacidad (simulado) - AHORA USA EL MÉTODO CORREGIDO
        color_fondo = self._color_con_opacidad(color_hex, 0.1)
        
        # Contenedor del símbolo (como el div del frontend)
        contenedor_simbolo = Table(
            [[Paragraph(f"<b>{simbolo}</b>", _estilo_simbolo(color_hex))]],
            colWidths=[ancho_simbolo - 2],
            rowHeights=[ancho_simbolo - 2],
        )
        contenedor_simbolo.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor(color_hex)),
            ('BACKGROUND', (0, 0), (-1, -1), color_fondo),
        ]))
        
        # Celda que combina símbolo y descripción
        celda = Table(
            [[
                contenedor_simbolo,
                Paragraph(descripcion, _estilo_descripcion()),
            ]],
            colWidths=[ancho_simbolo, ancho_descripcion],
        )
        
        celda.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, 0), 'CENTER'),
            ('ALIGN', (1, 0), (1, 0), 'LEFT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        
        return celda

    def _tabla_colores_diagnostico(self) -> Table:
        """
        Crea tabla con la leyenda de colores de diagnóstico.
        """
        datos = [
            ["Color", "Significado", "Código Clínico"],
            ["■ Rojo", "Indicado / Por realizar", "Tratamiento pendiente"],
            ["■ Azul", "Realizado / Completado", "Tratamiento realizado"],
            ["■ Verde", "Sano", "Sin patología"],
            ["■ Negro", "Ausente", "Diente no presente"],
        ]

        tabla = Table(
            datos,
            colWidths=[30 * mm, 60 * mm, 50 * mm],
            repeatRows=1,
        )

        # Definir colores para cada fila
        tabla.setStyle(TableStyle([
            # Encabezados
            ('BACKGROUND', (0, 0), (-1, 0), VERDE_MUY_CLARO),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            # Bordes
            ('GRID', (0, 0), (-1, -1), 0.3, VERDE_CLARO),
            ('LINEBELOW', (0, 0), (-1, 0), 0.5, VERDE_OSCURO),
            # Padding
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            # Colores específicos para el texto de la primera columna
            ('TEXTCOLOR', (0, 1), (0, 1), colors.HexColor(C_ROJO)),
            ('TEXTCOLOR', (0, 2), (0, 2), colors.HexColor(C_AZUL)),
            ('TEXTCOLOR', (0, 3), (0, 3), colors.HexColor(C_VERDE)),
            ('TEXTCOLOR', (0, 4), (0, 4), colors.HexColor(C_NEGRO)),
            # Fondos suaves para la segunda columna - USANDO EL MÉTODO CORREGIDO
            ('BACKGROUND', (1, 1), (1, 1), self._color_con_opacidad(C_ROJO, 0.1)),
            ('BACKGROUND', (1, 2), (1, 2), self._color_con_opacidad(C_AZUL, 0.1)),
            ('BACKGROUND', (1, 3), (1, 3), self._color_con_opacidad(C_VERDE, 0.1)),
            ('BACKGROUND', (1, 4), (1, 4), self._color_con_opacidad(C_NEGRO, 0.1)),
            # Filas alternadas
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [BLANCO, VERDE_MUY_CLARO]),
        ]))

        return tabla

    # Métodos auxiliares para mantener consistencia con otras secciones
    def sin_datos(self) -> List[Flowable]:
        """Mensaje cuando no hay datos (no aplica para simbología)."""
        return [Paragraph(
            "<i>Leyenda de simbología del odontograma no disponible</i>",
            ESTILOS["normal"],
        )]


# ═══════════════════════════════════════════════════════════════════════════
# EXPORTACIÓN
# ═══════════════════════════════════════════════════════════════════════════
__all__ = ['SeccionKSimbologiaOdontograma']