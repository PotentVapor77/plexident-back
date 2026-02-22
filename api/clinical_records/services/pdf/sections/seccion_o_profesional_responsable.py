# api/clinical_records/services/pdf/sections/seccion_o_profesional_responsable.py
"""
Sección O del Formulario 033: DATOS DEL PROFESIONAL RESPONSABLE

Muestra:
  • Fecha de apertura / atención
  • Hora de atención
  • Nombre y apellido del profesional responsable
  • Espacio para firma física
  • Espacio para sello físico

Fuente de datos:
  historial.fecha_atencion          → DateTimeField
  historial.odontologo_responsable  → FK Usuario
    usuario.nombres                 → str
    usuario.apellidos               → str
"""
from typing import List

from reportlab.platypus import Flowable, Table, TableStyle, Spacer, Paragraph, HRFlowable
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

from .base_section import (
    BaseSeccion,
    ANCHO_PAGINA,
    COLOR_PRIMARIO,
    COLOR_SECUNDARIO,
    COLOR_BORDE,
    COLOR_ACENTO,
    ESTILOS,
)


# ═══════════════════════════════════════════════════════════════════════════
# PALETA DE COLORES
# ═══════════════════════════════════════════════════════════════════════════
VERDE_OSCURO    = COLOR_PRIMARIO        # encabezado de sección
VERDE_CLARO     = COLOR_BORDE           # bordes tabla
VERDE_MUY_CLARO = COLOR_ACENTO          # fondos suaves
GRIS_HEADER     = colors.HexColor('#ECF0F1')
GRIS_TEXTO      = colors.HexColor('#2C3E50')
GRIS_ETIQUETA   = colors.HexColor('#5D6D7E')
GRIS_LINEA      = colors.HexColor('#BDC3C7')
BLANCO          = colors.white


# ═══════════════════════════════════════════════════════════════════════════
# ESTILOS LOCALES
# ═══════════════════════════════════════════════════════════════════════════
def _es(name, **kw) -> ParagraphStyle:
    defaults = dict(fontName='Helvetica', fontSize=8, textColor=GRIS_TEXTO, leading=10)
    defaults.update(kw)
    return ParagraphStyle(name, **defaults)


E_TITULO         = _es('O_titulo',    fontName='Helvetica-Bold', fontSize=11,
                        textColor=BLANCO, alignment=TA_CENTER, leading=13)
E_ETIQUETA       = _es('O_etiq',     fontName='Helvetica-Bold', fontSize=7,
                        textColor=GRIS_ETIQUETA, alignment=TA_LEFT, leading=9)
E_VALOR          = _es('O_val',      fontName='Helvetica-Bold', fontSize=10,
                        textColor=GRIS_TEXTO, alignment=TA_LEFT, leading=12)
E_VALOR_GRANDE   = _es('O_val_g',   fontName='Helvetica-Bold', fontSize=11,
                        textColor=GRIS_TEXTO, alignment=TA_LEFT, leading=13)
E_FIRMA_ETIQ     = _es('O_firma_e', fontName='Helvetica-Bold', fontSize=7,
                        textColor=GRIS_ETIQUETA, alignment=TA_CENTER, leading=9)
E_FIRMA_NOTA     = _es('O_firma_n', fontName='Helvetica-Oblique', fontSize=7,
                        textColor=GRIS_LINEA, alignment=TA_CENTER, leading=9)
E_SIN_DATOS      = _es('O_sin',     fontName='Helvetica-Oblique', fontSize=9,
                        textColor=GRIS_ETIQUETA, alignment=TA_CENTER, leading=12)


# ═══════════════════════════════════════════════════════════════════════════
# ANCHOS
# ═══════════════════════════════════════════════════════════════════════════
# Fila de datos: [Fecha] [Hora] [Nombre del profesional]
COL_FECHA      = 45 * mm
COL_HORA       = 30 * mm
COL_PROFESIONAL = ANCHO_PAGINA - COL_FECHA - COL_HORA   # ≈ 95 mm

# Fila de firma/sello: 50 / 50 de la página
COL_FIRMA      = ANCHO_PAGINA * 0.50
COL_SELLO      = ANCHO_PAGINA - COL_FIRMA


# ═══════════════════════════════════════════════════════════════════════════
# CLASE PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════
class SeccionOProfesionalResponsable(BaseSeccion):
    """
    Sección O del Formulario 033: DATOS DEL PROFESIONAL RESPONSABLE

    Layout:
      ┌──────────────────────────────────────────────────────────────────┐
      │  O. DATOS DEL PROFESIONAL RESPONSABLE  (encabezado verde)       │
      ├───────────────────┬───────────────┬─────────────────────────────┤
      │ FECHA DE ATENCIÓN │ HORA          │ NOMBRE Y APELLIDOS          │
      │ 22/02/2026        │ 10:30         │ Dr. Juan Pérez              │
      ├───────────────────┴───────────────┴─────────────────────────────┤
      │          FIRMA DEL PROFESIONAL    │    SELLO DEL PROFESIONAL    │
      │                                   │                             │
      │   ___________________________     │   [ espacio sello ]        │
      │   Firma                           │                             │
      └───────────────────────────────────┴─────────────────────────────┘
    """

    @property
    def nombre_seccion(self) -> str:
        return 'O. Datos del Profesional Responsable'

    @property
    def es_opcional(self) -> bool:
        return False  # Siempre requerida

    # ------------------------------------------------------------------
    # Punto de entrada
    # ------------------------------------------------------------------
    def construir(self, historial) -> List[Flowable]:
        elementos: List[Flowable] = []

        elementos.append(self._encabezado_seccion())
        elementos.append(Spacer(1, 3))
        elementos.append(self._fila_datos(historial))
        elementos.append(Spacer(1, 2))
        elementos.append(self._fila_firma_sello(historial))
        elementos.append(Spacer(1, 8))

        return elementos

    # ------------------------------------------------------------------
    # Encabezado de sección
    # ------------------------------------------------------------------
    def _encabezado_seccion(self) -> Table:
        t = Table(
            [[Paragraph('O. DATOS DEL PROFESIONAL RESPONSABLE', E_TITULO)]],
            colWidths=[ANCHO_PAGINA],
        )
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), VERDE_OSCURO),
            ('TOPPADDING',    (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        return t

    # ------------------------------------------------------------------
    # Fila de datos: fecha | hora | nombre profesional
    # ------------------------------------------------------------------
    def _fila_datos(self, historial) -> Table:
        fecha_str, hora_str = self._extraer_fecha_hora(historial)
        nombre_profesional  = self._extraer_nombre_profesional(historial)

        def celda(etiqueta: str, valor: str) -> Table:
            """Mini-tabla interna: etiqueta arriba, valor abajo."""
            t = Table(
                [
                    [Paragraph(etiqueta, E_ETIQUETA)],
                    [Paragraph(valor,    E_VALOR)],
                ],
                colWidths=['100%'],
            )
            t.setStyle(TableStyle([
                ('LEFTPADDING',   (0, 0), (-1, -1), 0),
                ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
                ('TOPPADDING',    (0, 0), (-1, -1), 1),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ]))
            return t

        tabla = Table(
            [[
                celda('FECHA DE ATENCIÓN', fecha_str),
                celda('HORA', hora_str),
                celda('NOMBRE Y APELLIDOS DEL PROFESIONAL', nombre_profesional),
            ]],
            colWidths=[COL_FECHA, COL_HORA, COL_PROFESIONAL],
        )
        tabla.setStyle(TableStyle([
            ('BOX',           (0, 0), (-1, -1), 1.0,  VERDE_CLARO),
            ('LINEBEFORE',    (1, 0), (1, 0),   0.5,  VERDE_CLARO),
            ('LINEBEFORE',    (2, 0), (2, 0),   0.5,  VERDE_CLARO),
            ('BACKGROUND',    (0, 0), (-1, -1), VERDE_MUY_CLARO),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING',    (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING',   (0, 0), (-1, -1), 6),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
        ]))
        return tabla

    # ------------------------------------------------------------------
    # Fila de firma y sello (espacios físicos)
    # ------------------------------------------------------------------
    def _fila_firma_sello(self, historial) -> Table:
        """
        Dos bloques lado a lado con espacio para firma y sello físicos.
        Altura fija de ~28 mm para dejar lugar suficiente.
        """
        ALTO_ESPACIO = 28 * mm

        # ── Bloque FIRMA ──────────────────────────────────────────────
        nombre = self._extraer_nombre_profesional(historial)

        bloque_firma = Table(
            [
                [Paragraph('FIRMA DEL PROFESIONAL', E_FIRMA_ETIQ)],
                # Espacio en blanco donde se estampará la firma física
                [Paragraph('', E_FIRMA_NOTA)],
                # Línea de firma
                [HRFlowable(
                    width='80%',
                    thickness=0.8,
                    color=GRIS_LINEA,
                    spaceBefore=2,
                    spaceAfter=1,
                    hAlign='CENTER',
                )],
                [Paragraph(nombre, E_FIRMA_ETIQ)],
            ],
            colWidths=[COL_FIRMA - 4 * mm],
            rowHeights=[None, ALTO_ESPACIO - 20 * mm, None, None],
        )
        bloque_firma.setStyle(TableStyle([
            ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN',        (0, 0), (-1, -1), 'BOTTOM'),
            ('TOPPADDING',    (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ]))

        # ── Bloque SELLO ──────────────────────────────────────────────
        bloque_sello = Table(
            [
                [Paragraph('SELLO DEL PROFESIONAL', E_FIRMA_ETIQ)],
                [Paragraph('', E_FIRMA_NOTA)],
            ],
            colWidths=[COL_SELLO - 4 * mm],
            rowHeights=[None, ALTO_ESPACIO - 10 * mm],
        )
        bloque_sello.setStyle(TableStyle([
            ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING',    (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
            # Borde punteado simulado con borde sólido fino en el bloque de sello
            ('BOX',           (0, 0), (-1, -1), 0.5, GRIS_LINEA),
        ]))

        # ── Contenedor de ambos bloques ───────────────────────────────
        contenedor = Table(
            [[bloque_firma, bloque_sello]],
            colWidths=[COL_FIRMA, COL_SELLO],
            rowHeights=[ALTO_ESPACIO],
        )
        contenedor.setStyle(TableStyle([
            ('BOX',           (0, 0), (-1, -1), 1.0,  VERDE_CLARO),
            ('LINEBEFORE',    (1, 0), (1, 0),   0.5,  VERDE_CLARO),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING',    (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING',   (0, 0), (-1, -1), 4),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
        ]))
        return contenedor

    # ------------------------------------------------------------------
    # Helpers de extracción
    # ------------------------------------------------------------------
    @staticmethod
    def _extraer_fecha_hora(historial):
        """
        Extrae fecha y hora de historial.fecha_atencion.
        Devuelve (fecha_str, hora_str) formateados.
        """
        fecha_atencion = getattr(historial, 'fecha_atencion', None)
        if fecha_atencion is None:
            return '—', '—'
        try:
            fecha_str = fecha_atencion.strftime('%d / %m / %Y')
            hora_str  = fecha_atencion.strftime('%H:%M')
        except AttributeError:
            # Si es string
            raw = str(fecha_atencion)
            fecha_str = raw[:10] if len(raw) >= 10 else raw
            hora_str  = raw[11:16] if len(raw) >= 16 else '—'
        return fecha_str, hora_str

    @staticmethod
    def _extraer_nombre_profesional(historial) -> str:
        """
        Extrae nombre completo del odontólogo responsable.
        """
        odontologo = getattr(historial, 'odontologo_responsable', None)
        if odontologo is None:
            return '—'
        nombres   = getattr(odontologo, 'nombres',   '') or ''
        apellidos = getattr(odontologo, 'apellidos', '') or ''
        nombre_completo = f"{nombres} {apellidos}".strip()
        return nombre_completo if nombre_completo else '—'

    # ------------------------------------------------------------------
    # Mensaje sin datos (no debería ocurrir — sección obligatoria)
    # ------------------------------------------------------------------
    def sin_datos(self) -> List[Flowable]:
        return [
            Paragraph(
                '<i>No hay datos del profesional responsable registrados</i>',
                ESTILOS['normal'],
            )
        ]


# ═══════════════════════════════════════════════════════════════════════════
# EXPORTACIÓN
# ═══════════════════════════════════════════════════════════════════════════
__all__ = ['SeccionOProfesionalResponsable']