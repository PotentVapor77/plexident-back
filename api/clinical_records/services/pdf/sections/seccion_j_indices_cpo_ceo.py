# api/clinical_records/services/pdf/sections/seccion_j_indices_cpo_ceo.py
"""
Sección J del Formulario 033: ÍNDICES CPO-ceo

Estructura del modelo IndiceCariesSnapshot:
  - Dentición permanente (CPO):
      cpo_c  → Dientes cariados
      cpo_p  → Dientes perdidos por caries
      cpo_o  → Dientes obturados
      cpo_total → CPO total
  - Dentición temporal (ceo):
      ceo_c  → Dientes temporales cariados
      ceo_e  → Dientes temporales con extracción indicada
      ceo_o  → Dientes temporales obturados
      ceo_total → ceo total
  - fecha (auto_now_add)

Diseño:
  - Encabezado verde oscuro
  - Dos tablas: CPO (permanente) y ceo (temporal)
  - Fila de totales resaltada en cada tabla
  - Interpretación del riesgo según OMS
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
    COLOR_PRIMARIO,
    COLOR_SECUNDARIO,
    COLOR_BORDE,
    COLOR_ACENTO,
)

# ═══════════════════════════════════════════════════════════════════════════
# COLORES
# ═══════════════════════════════════════════════════════════════════════════
VERDE_OSCURO    = COLOR_PRIMARIO
VERDE_MEDIO     = COLOR_SECUNDARIO
VERDE_CLARO     = COLOR_BORDE
VERDE_MUY_CLARO = COLOR_ACENTO
GRIS_TEXTO      = colors.HexColor('#2C3E50')
GRIS_ETIQUETA   = colors.HexColor('#5D6D7E')
GRIS_HEADER     = colors.HexColor('#ECF0F1')
AZUL_TOTAL      = colors.HexColor('#EBF5FB')
BLANCO          = colors.white

# Colores de riesgo OMS (CPO-D)
RIESGO_MUY_BAJO = colors.HexColor('#D5F5E3')   # 0.0 – 1.1
RIESGO_BAJO     = colors.HexColor('#A9DFBF')   # 1.2 – 2.6
RIESGO_MODERADO = colors.HexColor('#FAD7A0')   # 2.7 – 4.4
RIESGO_ALTO     = colors.HexColor('#F1948A')   # 4.5 – 6.5
RIESGO_MUY_ALTO = colors.HexColor('#EC7063')   # > 6.5


# ═══════════════════════════════════════════════════════════════════════════
# ESTILOS
# ═══════════════════════════════════════════════════════════════════════════
def _e_titulo():
    return ParagraphStyle('TituloJ', fontSize=11, fontName='Helvetica-Bold',
                          textColor=BLANCO, alignment=TA_CENTER, leading=13)

def _e_subtitulo():
    return ParagraphStyle('SubJ', fontSize=9, fontName='Helvetica-Bold',
                          textColor=BLANCO, alignment=TA_LEFT, leading=11)

def _e_header():
    return ParagraphStyle('HdrJ', fontSize=8, fontName='Helvetica-Bold',
                          textColor=GRIS_ETIQUETA, alignment=TA_CENTER, leading=10)

def _e_celda():
    return ParagraphStyle('CelJ', fontSize=10, fontName='Helvetica',
                          textColor=GRIS_TEXTO, alignment=TA_CENTER, leading=12)

def _e_celda_bold():
    return ParagraphStyle('CelBJ', fontSize=11, fontName='Helvetica-Bold',
                          textColor=VERDE_OSCURO, alignment=TA_CENTER, leading=13)

def _e_etiqueta():
    return ParagraphStyle('EtJ', fontSize=8, fontName='Helvetica-Bold',
                          textColor=GRIS_ETIQUETA, alignment=TA_LEFT, leading=10)

def _e_valor():
    return ParagraphStyle('ValJ', fontSize=9, fontName='Helvetica',
                          textColor=GRIS_TEXTO, alignment=TA_LEFT, leading=11)

def _e_riesgo_label():
    return ParagraphStyle('RiesgoLbl', fontSize=8, fontName='Helvetica-Bold',
                          textColor=GRIS_ETIQUETA, alignment=TA_CENTER, leading=10)

def _e_riesgo_val():
    return ParagraphStyle('RiesgoVal', fontSize=9, fontName='Helvetica-Bold',
                          textColor=GRIS_TEXTO, alignment=TA_CENTER, leading=11)


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════
def _val(obj, campo: str) -> str:
    v = getattr(obj, campo, None)
    return str(v) if v is not None else '0'


def _riesgo_cpo(total) -> tuple:
    """
    Devuelve (texto_nivel, color_fondo) según clasificación OMS para CPO-D.
    """
    try:
        t = int(total)
    except (TypeError, ValueError):
        return ('—', BLANCO)

    if t <= 1:
        return ('Muy bajo (0–1)', RIESGO_MUY_BAJO)
    elif t <= 2:
        return ('Bajo (2)', RIESGO_BAJO)
    elif t <= 4:
        return ('Moderado (3–4)', RIESGO_MODERADO)
    elif t <= 6:
        return ('Alto (5–6)', RIESGO_ALTO)
    else:
        return ('Muy alto (>6)', RIESGO_MUY_ALTO)


# ═══════════════════════════════════════════════════════════════════════════
# CLASE PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════
class SeccionJIndicesCPOceo(BaseSeccion):
    """
    Sección J del Formulario 033: ÍNDICES CPO-ceo

    Lee los datos de historial.indices_caries (IndiceCariesSnapshot).
    """

    @property
    def nombre_seccion(self) -> str:
        return 'J. Índices CPO-ceo'

    @property
    def es_opcional(self) -> bool:
        return False

    # ──────────────────────────────────────────────────────────────────────
    def construir(self, historial) -> List[Flowable]:
        elementos = []

        elementos.append(self._encabezado('J. ÍNDICES CPO-ceo'))
        elementos.append(Spacer(1, 2))

        snap = getattr(historial, 'indices_caries', None)
        if not snap:
            elementos.extend(self.sin_datos())
            elementos.append(Spacer(1, 8))
            return elementos

        # ── CPO (permanente) ──────────────────────────────────────────────
        elementos.append(self._subtitulo('DENTICIÓN PERMANENTE — CPO-D'))
        elementos.append(Spacer(1, 1))
        elementos.append(self._tabla_cpo(snap))
        elementos.append(Spacer(1, 2))

        # Riesgo OMS
        total_cpo = getattr(snap, 'cpo_total', 0)
        elementos.append(self._fila_riesgo(total_cpo))
        elementos.append(Spacer(1, 6))

        # ── ceo (temporal) ────────────────────────────────────────────────
        elementos.append(self._subtitulo('DENTICIÓN TEMPORAL — ceo-d'))
        elementos.append(Spacer(1, 1))
        elementos.append(self._tabla_ceo(snap))
        elementos.append(Spacer(1, 6))

        # ── Fecha del snapshot ────────────────────────────────────────────
        fecha_snap = getattr(snap, 'fecha', None)
        fecha_str = str(fecha_snap)[:10] if fecha_snap else '—'
        elementos.append(self._fila_dato('Fecha de Evaluación', fecha_str))
        elementos.append(Spacer(1, 8))

        return elementos

    # ──────────────────────────────────────────────────────────────────────
    # Componentes visuales
    # ──────────────────────────────────────────────────────────────────────
    def _encabezado(self, texto: str) -> Table:
        t = Table([[Paragraph(texto, _e_titulo())]], colWidths=[ANCHO_PAGINA])
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), VERDE_OSCURO),
            ('TOPPADDING',    (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        return t

    def _subtitulo(self, texto: str) -> Table:
        t = Table([[Paragraph(texto, _e_subtitulo())]], colWidths=[ANCHO_PAGINA])
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), VERDE_MEDIO),
            ('TOPPADDING',    (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING',   (0, 0), (-1, -1), 6),
        ]))
        return t

    def _tabla_cpo(self, snap) -> Table:
        """
        Tabla 4 columnas: C | P | O | CPO Total
        """
        # Anchos: 4 columnas simétricas
        col_w = ANCHO_PAGINA / 4

        hdr = [
            Paragraph('C\nCariados', _e_header()),
            Paragraph('P\nPerdidos', _e_header()),
            Paragraph('O\nObturados', _e_header()),
            Paragraph('CPO Total', _e_header()),
        ]

        fila = [
            Paragraph(_val(snap, 'cpo_c'), _e_celda()),
            Paragraph(_val(snap, 'cpo_p'), _e_celda()),
            Paragraph(_val(snap, 'cpo_o'), _e_celda()),
            Paragraph(_val(snap, 'cpo_total'), _e_celda_bold()),
        ]

        t = Table([hdr, fila], colWidths=[col_w] * 4)
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0), GRIS_HEADER),
            ('BACKGROUND',    (0, 1), (-2, 1), BLANCO),
            ('BACKGROUND',    (-1, 1), (-1, 1), AZUL_TOTAL),
            ('FONTNAME',      (-1, 1), (-1, 1), 'Helvetica-Bold'),
            ('GRID',          (0, 0), (-1, -1), 0.5, VERDE_CLARO),
            ('BOX',           (0, 0), (-1, -1), 1,   VERDE_CLARO),
            ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING',    (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('FONTSIZE',      (0, 1), (-1, 1), 14),
        ]))
        return t

    def _tabla_ceo(self, snap) -> Table:
        """
        Tabla 4 columnas: c | e | o | ceo Total
        """
        col_w = ANCHO_PAGINA / 4

        hdr = [
            Paragraph('c\nCariados', _e_header()),
            Paragraph('e\nExtracción Indicada', _e_header()),
            Paragraph('o\nObturados', _e_header()),
            Paragraph('ceo Total', _e_header()),
        ]

        fila = [
            Paragraph(_val(snap, 'ceo_c'), _e_celda()),
            Paragraph(_val(snap, 'ceo_e'), _e_celda()),
            Paragraph(_val(snap, 'ceo_o'), _e_celda()),
            Paragraph(_val(snap, 'ceo_total'), _e_celda_bold()),
        ]

        t = Table([hdr, fila], colWidths=[col_w] * 4)
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0), GRIS_HEADER),
            ('BACKGROUND',    (0, 1), (-2, 1), BLANCO),
            ('BACKGROUND',    (-1, 1), (-1, 1), AZUL_TOTAL),
            ('FONTNAME',      (-1, 1), (-1, 1), 'Helvetica-Bold'),
            ('GRID',          (0, 0), (-1, -1), 0.5, VERDE_CLARO),
            ('BOX',           (0, 0), (-1, -1), 1,   VERDE_CLARO),
            ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING',    (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('FONTSIZE',      (0, 1), (-1, 1), 14),
        ]))
        return t

    def _fila_riesgo(self, total_cpo) -> Table:
        """
        Fila coloreada que muestra el nivel de riesgo OMS para el CPO-D.
        """
        nivel, color_fondo = _riesgo_cpo(total_cpo)

        t = Table(
            [[
                Paragraph('Nivel de Riesgo OMS (CPO-D)', _e_riesgo_label()),
                Paragraph(nivel, _e_riesgo_val()),
            ]],
            colWidths=[60 * mm, 110 * mm],
        )
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (0, 0), VERDE_MUY_CLARO),
            ('BACKGROUND',    (1, 0), (1, 0), color_fondo),
            ('BOX',           (0, 0), (-1, -1), 0.5, VERDE_CLARO),
            ('LINEAFTER',     (0, 0), (0, 0),   0.5, VERDE_CLARO),
            ('TOPPADDING',    (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING',   (0, 0), (-1, -1), 4),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN',         (1, 0), (1, 0),   'CENTER'),
        ]))
        return t

    def _fila_dato(self, etiqueta: str, valor: str) -> Table:
        t = Table(
            [[Paragraph(etiqueta.upper(), _e_etiqueta()),
              Paragraph(valor, _e_valor())]],
            colWidths=[60 * mm, 110 * mm],
        )
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (0, 0), VERDE_MUY_CLARO),
            ('BACKGROUND',    (1, 0), (1, 0), BLANCO),
            ('BOX',           (0, 0), (-1, -1), 0.5, VERDE_CLARO),
            ('LINEAFTER',     (0, 0), (0, 0),   0.5, VERDE_CLARO),
            ('TOPPADDING',    (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING',   (0, 0), (-1, -1), 4),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ]))
        return t


# ═══════════════════════════════════════════════════════════════════════════
# EXPORTACIÓN
# ═══════════════════════════════════════════════════════════════════════════
__all__ = ['SeccionJIndicesCPOceo']