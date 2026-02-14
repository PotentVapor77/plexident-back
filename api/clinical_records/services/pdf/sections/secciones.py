# api/clinical_records/services/pdf/sections/secciones.py
"""
Implementaciones concretas de cada sección del PDF del historial clínico.

Agregar una nueva sección:
  1. Crear clase que herede de BaseSeccion
  2. Implementar nombre_seccion y construir()
  3. Añadirla en ClinicalRecordPDFBuilder.SECCIONES_DISPONIBLES
"""
from typing import List

from reportlab.platypus import Flowable, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from .base_section import (
    BaseSeccion, ESTILOS, ANCHO_PAGINA,
    COLOR_PRIMARIO, COLOR_SECUNDARIO, COLOR_ACENTO, COLOR_BORDE,
    COLOR_EXITO, COLOR_ADVERTENCIA, COLOR_VACIO,
)

# ─── Colores que mapean exactamente al diseño TSX ───────────────────────────
_BRAND_600  = colors.HexColor('#1570EF')   # barra de acento izquierda
_BRAND_100  = colors.HexColor('#D1E9FF')   # fondo badge condición
_BRAND_200  = colors.HexColor('#B2DDFF')   # borde badge condición
_BRAND_700  = colors.HexColor('#175CD3')   # texto badge condición
_GRAY_50    = colors.HexColor('#F9FAFB')   # bg-gray-50 (cards)
_GRAY_100   = colors.HexColor('#F2F4F7')   # border interior blanco
_GRAY_200   = colors.HexColor('#EAECF0')   # border-gray-200
_GRAY_300   = colors.HexColor('#D0D5DD')   # divisor horizontal
_GRAY_500   = colors.HexColor('#667085')   # texto-gris-medio
_GRAY_700   = colors.HexColor('#344054')   # texto subtítulos
_GRAY_800   = colors.HexColor('#1D2939')   # etiquetas uppercase
_GRAY_900   = colors.HexColor('#101828')   # valores principales
_PINK_50    = colors.HexColor('#FDF2FA')   # femenino bg
_PINK_200   = colors.HexColor('#FCCEEE')   # femenino border
_PINK_700   = colors.HexColor('#C11574')   # femenino texto
_BLUE_50    = colors.HexColor('#EFF8FF')   # masculino bg
_BLUE_200   = colors.HexColor('#B2DDFF')   # masculino border
_BLUE_700   = colors.HexColor('#175CD3')   # masculino texto


def _lbl(text: str) -> Paragraph:
    """Etiqueta uppercase pequeña — equivale al <p className="text-xs font-semibold ...">"""
    return Paragraph(text.upper(), ParagraphStyle(
        f'Lbl_{text[:8]}', fontSize=7, fontName='Helvetica-Bold',
        textColor=_GRAY_800, spaceAfter=0, spaceBefore=0,
    ))


def _val(text, mono=False, bold=False, size=8.5, color=None) -> Paragraph:
    """Valor del campo — equivale al <p className="text-sm text-gray-900">"""
    font = 'Courier' if mono else ('Helvetica-Bold' if bold else 'Helvetica')
    return Paragraph(
        str(text) if text not in (None, '', []) else '—',
        ParagraphStyle(
            f'Val_{str(text)[:8]}', fontSize=size, fontName=font,
            textColor=color or _GRAY_900,
        ),
    )


def _card(label: str, value_para: Paragraph, with_bar=True, col_width=None) -> Table:
    """
    Tarjeta individual con fondo gris-50, borde gris-200 y barra de acento azul.
    Replica exactamente la estructura de cada celda del grid en el TSX.
    """
    w = col_width or (ANCHO_PAGINA / 3)

    if with_bar:
        # Barra de acento vertical azul (w-1 h-4 bg-brand-600)
        barra = Table(
            [[' ']],
            colWidths=[2 * mm],
            rowHeights=[5 * mm],
        )
        barra.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), _BRAND_600),
            ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ]))
        header = Table(
            [[barra, label if isinstance(label, Paragraph) else _lbl(label)]],
            colWidths=[3 * mm, w - 3 * mm - 6 * mm],
        )
        header.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 2),
        ]))
    else:
        header = _lbl(label) if isinstance(label, str) else label

    # Caja interior blanca para el valor
    value_box = Table(
        [[value_para]],
        colWidths=[w - 8 * mm],
    )
    value_box.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), colors.white),
        ('BOX',           (0, 0), (-1, -1), 0.4, _GRAY_200),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 5),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 5),
    ]))

    # Card exterior gris-50
    card = Table(
        [[header], [value_box]],
        colWidths=[w - 6 * mm],
    )
    card.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), _GRAY_50),
        ('BOX',           (0, 0), (-1, -1), 0.5, _GRAY_200),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
    ]))
    return card


def _sexo_badge(sexo) -> Table:
    """Badge coloreado para el sexo — replica el div con clases dinámicas del TSX."""
    sexo_str = str(sexo or '').lower()
    if 'f' in sexo_str:
        bg, border, fg, texto = _PINK_50, _PINK_200, _PINK_700, 'Femenino'
    elif 'm' in sexo_str:
        bg, border, fg, texto = _BLUE_50, _BLUE_200, _BLUE_700, 'Masculino'
    else:
        bg, border, fg, texto = _GRAY_50, _GRAY_200, _GRAY_700, str(sexo or '—')

    badge = Table(
        [[Paragraph(texto, ParagraphStyle(
            'BadgeSexo', fontSize=8.5, fontName='Helvetica-Bold', textColor=fg,
            alignment=TA_CENTER,
        ))]],
        colWidths=[24 * mm],
    )
    badge.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), bg),
        ('BOX',           (0, 0), (-1, -1), 0.5, border),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING',   (0, 0), (-1, -1), 4),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
    ]))
    return badge


def _condition_badge() -> Table:
    """Badge circular con letra 'A' (Adulto) — replica el div rounded-full bg-brand-100."""
    badge = Table(
        [[Paragraph('A', ParagraphStyle(
            'BadgeCond', fontSize=9, fontName='Helvetica-Bold',
            textColor=_BRAND_700, alignment=TA_CENTER,
        ))]],
        colWidths=[8 * mm],
        rowHeights=[8 * mm],
    )
    badge.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, -1), _BRAND_100),
        ('BOX',           (0, 0), (-1, -1), 0.5, _BRAND_200),
        ('TOPPADDING',    (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('LEFTPADDING',   (0, 0), (-1, -1), 1),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 1),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return badge


# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 1 — A. DATOS DE ESTABLECIMIENTO Y PACIENTE  (Formulario 033)
# Replica fielmente EstablecimientoPacienteSection.tsx
# ═══════════════════════════════════════════════════════════════════════════════
class SeccionEstablecimientoPaciente(BaseSeccion):
    """
    Sección A completa: datos institucionales + datos del paciente.
    Layout idéntico al componente TSX:
      - Grid 3 columnas para establecimiento
      - Divisor con texto centrado "DATOS DEL PACIENTE"
      - Grid 4 columnas para paciente (Nombres / Apellidos / Sexo / Edad+Condición)
    """

    nombre_seccion = 'A. Datos de Establecimiento y Paciente'
    es_opcional = False

    # Ancho de cada columna del grid de establecimiento (3 cols)
    _W3 = ANCHO_PAGINA / 3

    # Anchos del grid de paciente (4 cols, última subdivida en 2)
    _WN = ANCHO_PAGINA * 0.28   # Nombres
    _WA = ANCHO_PAGINA * 0.28   # Apellidos
    _WS = ANCHO_PAGINA * 0.22   # Sexo
    _WR = ANCHO_PAGINA * 0.22   # Edad + Condición (dividida en dos sub-cols)

    def construir(self, historial) -> List[Flowable]:
        elementos = []

        # ── Encabezado de sección (título + subtítulo) ─────────────────────
        titulo_style = ParagraphStyle(
            'SecATitulo', fontSize=11, fontName='Helvetica-Bold',
            textColor=_GRAY_900, spaceAfter=2,
        )
        sub_style = ParagraphStyle(
            'SecASub', fontSize=8, fontName='Helvetica',
            textColor=_GRAY_500, spaceAfter=0,
        )

        header_box = Table(
            [
                [Paragraph('A. Datos de establecimiento y paciente (Formulario 033)', titulo_style)],
                [Paragraph('Información institucional y datos del paciente según formato oficial', sub_style)],
            ],
            colWidths=[ANCHO_PAGINA],
        )
        header_box.setStyle(TableStyle([
            ('TOPPADDING',    (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('LINEBELOW',     (0, -1), (-1, -1), 0.5, _GRAY_300),
        ]))
        elementos.append(header_box)
        elementos.append(Spacer(1, 8))

        # ── Sub-título "Datos del Establecimiento" ─────────────────────────
        elementos.append(Paragraph(
            'DATOS DEL ESTABLECIMIENTO',
            ParagraphStyle('SubSecA', fontSize=8, fontName='Helvetica-Bold',
                           textColor=_GRAY_700, spaceAfter=5),
        ))

        # ── Grid 3 columnas — fila 1: Institución | Unicódigo | Establecimiento
        gap = 2 * mm
        w3 = (ANCHO_PAGINA - 2 * gap) / 3

        fila1 = Table(
            [[
                _card('INSTITUCIÓN DEL SISTEMA',
                      _val(historial.institucion_sistema or 'SISTEMA NACIONAL DE SALUD'), col_width=w3),
                _card('UNICÓDIGO',
                      _val(historial.unicodigo or 'No especificado', mono=True), col_width=w3),
                _card('ESTABLECIMIENTO DE SALUD',
                      _val(historial.establecimiento_salud or 'No especificado'), col_width=w3),
            ]],
            colWidths=[w3, w3, w3],
            spaceAfter=gap,
        )
        fila1.setStyle(TableStyle([
            ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
            ('ALIGN',         (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ]))
        elementos.append(fila1)
        elementos.append(Spacer(1, gap))

        # ── Grid 3 columnas — fila 2: HC Única | Archivo | Hoja
        hoja_val = Table(
            [[Paragraph(str(historial.numero_hoja or '1'), ParagraphStyle(
                'HojaVal', fontSize=14, fontName='Helvetica-Bold',
                textColor=_GRAY_900, alignment=TA_CENTER,
            ))]],
            colWidths=[w3 - 14 * mm],
        )
        hoja_val.setStyle(TableStyle([
            ('ALIGN',  (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))

        fila2 = Table(
            [[
                _card('NÚMERO DE HISTORIA CLÍNICA ÚNICA',
                      _val(historial.numero_historia_clinica_unica or 'No asignado', mono=True), col_width=w3),
                _card('NÚMERO DE ARCHIVO',
                      _val(historial.numero_archivo or 'ARCH-XXXXX', mono=True), col_width=w3),
                _card('No. HOJA', hoja_val, col_width=w3),
            ]],
            colWidths=[w3, w3, w3],
        )
        fila2.setStyle(TableStyle([
            ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ]))
        elementos.append(fila2)
        elementos.append(Spacer(1, 8))

        # ── Divisor con texto centrado "DATOS DEL PACIENTE" ───────────────
        divisor = Table(
            [[
                Table([['']], colWidths=[ANCHO_PAGINA * 0.35]),
                Paragraph('DATOS DEL PACIENTE', ParagraphStyle(
                    'DivPac', fontSize=7.5, fontName='Helvetica-Bold',
                    textColor=_GRAY_500, alignment=TA_CENTER,
                )),
                Table([['']], colWidths=[ANCHO_PAGINA * 0.35]),
            ]],
            colWidths=[ANCHO_PAGINA * 0.35, ANCHO_PAGINA * 0.30, ANCHO_PAGINA * 0.35],
        )
        divisor.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (0, 0),  0.5, _GRAY_300),
            ('LINEABOVE', (2, 0), (2, 0),  0.5, _GRAY_300),
            ('TOPPADDING',    (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
            ('ALIGN',         (1, 0), (1, 0), 'CENTER'),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elementos.append(divisor)
        elementos.append(Spacer(1, 6))

        # ── Sub-título "Información del Paciente" ──────────────────────────
        elementos.append(Paragraph(
            'INFORMACIÓN DEL PACIENTE',
            ParagraphStyle('SubSecPac', fontSize=8, fontName='Helvetica-Bold',
                           textColor=_GRAY_700, spaceAfter=5),
        ))

        # ── Grid 4 columnas paciente ───────────────────────────────────────
        paciente = historial.paciente
        nombres  = getattr(paciente, 'nombres',   None) if paciente else None
        apellidos = getattr(paciente, 'apellidos', None) if paciente else None
        sexo     = getattr(paciente, 'sexo',      None) if paciente else None
        edad     = getattr(paciente, 'edad',       None) if paciente else None

        wn = self._WN
        wa = self._WA
        ws = self._WS
        wr = self._WR
        sub_w = wr / 2

        # Columna Nombres
        col_nombres = _card('NOMBRES', _val(nombres), with_bar=False, col_width=wn)

        # Columna Apellidos
        col_apellidos = _card('APELLIDOS', _val(apellidos), with_bar=False, col_width=wa)

        # Columna Sexo — badge coloreado centrado
        sexo_inner = Table(
            [[_sexo_badge(sexo)]],
            colWidths=[ws - 8 * mm],
        )
        sexo_inner.setStyle(TableStyle([
            ('ALIGN',  (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('BOX', (0, 0), (-1, -1), 0.4, _GRAY_200),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        col_sexo_outer = Table(
            [[_lbl('SEXO')], [sexo_inner]],
            colWidths=[ws - 6 * mm],
        )
        col_sexo_outer.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), _GRAY_50),
            ('BOX', (0, 0), (-1, -1), 0.5, _GRAY_200),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))

        # Columna Edad — número grande + "años"
        edad_inner_content = Table(
            [[
                Paragraph(str(edad) if edad is not None else '—', ParagraphStyle(
                    'EdadNum', fontSize=14, fontName='Helvetica-Bold',
                    textColor=_GRAY_900, alignment=TA_CENTER,
                )),
                Paragraph('años', ParagraphStyle(
                    'EdadUnit', fontSize=7, fontName='Helvetica',
                    textColor=_GRAY_500,
                )),
            ]],
            colWidths=[sub_w * 0.55, sub_w * 0.45],
        )
        edad_inner_content.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING',   (0, 0), (-1, -1), 2),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 2),
            ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        col_edad = _card('EDAD', edad_inner_content, with_bar=False, col_width=sub_w)

        # Columna Condición — badge circular "A"
        cond_inner = Table(
            [[_condition_badge()]],
            colWidths=[sub_w - 8 * mm],
        )
        cond_inner.setStyle(TableStyle([
            ('ALIGN',  (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('BOX', (0, 0), (-1, -1), 0.4, _GRAY_200),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        col_cond = Table(
            [[_lbl('CONDICIÓN')], [cond_inner]],
            colWidths=[sub_w - 6 * mm],
        )
        col_cond.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), _GRAY_50),
            ('BOX', (0, 0), (-1, -1), 0.5, _GRAY_200),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))

        # Sub-grid edad + condición
        sub_grid = Table(
            [[col_edad, col_cond]],
            colWidths=[sub_w, sub_w],
        )
        sub_grid.setStyle(TableStyle([
            ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ]))

        # Grid completo de paciente
        grid_paciente = Table(
            [[col_nombres, col_apellidos, col_sexo_outer, sub_grid]],
            colWidths=[wn, wa, ws, wr],
        )
        grid_paciente.setStyle(TableStyle([
            ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ]))
        elementos.append(grid_paciente)
        elementos.append(Spacer(1, 8))

        # ── Pie de sección ─────────────────────────────────────────────────
        pie = Table(
            [[
                Table([['  ']], colWidths=[2.5 * mm], rowHeights=[2.5 * mm]),
                Paragraph('Sección A completada', ParagraphStyle(
                    'PieSecA', fontSize=7, fontName='Helvetica',
                    textColor=_GRAY_500,
                )),
            ]],
            colWidths=[4 * mm, ANCHO_PAGINA - 4 * mm],
        )
        pie.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), _BRAND_600),
            ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING',  (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('LINEABOVE',   (0, 0), (-1, 0), 0.5, _GRAY_200),
        ]))
        elementos.append(pie)
        elementos.append(Spacer(1, 10))

        return elementos


# Aliases para compatibilidad con el registro anterior del builder
SeccionEncabezado    = SeccionEstablecimientoPaciente
SeccionDatosPaciente = SeccionEstablecimientoPaciente


# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 3 — MOTIVO DE CONSULTA Y ENFERMEDAD ACTUAL
# ═══════════════════════════════════════════════════════════════════════════════
class SeccionMotivoConsulta(BaseSeccion):
    """Secciones B y C del formulario 033."""

    nombre_seccion = 'Motivo de Consulta'

    def construir(self, historial) -> List[Flowable]:
        motivo = historial.motivo_consulta
        enfermedad = historial.enfermedad_actual

        if not motivo and not enfermedad:
            return []

        elementos = self.encabezado_seccion('B / C. Motivo de Consulta y Enfermedad Actual')
        elementos.append(self.fila_dato('Motivo de Consulta:', motivo))
        elementos.append(self.fila_dato('Enfermedad Actual:', enfermedad))
        elementos.append(Spacer(1, 6))
        return elementos


# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 4 — CONSTANTES VITALES
# ═══════════════════════════════════════════════════════════════════════════════
class SeccionConstantesVitales(BaseSeccion):
    """Signos vitales del paciente (sección F)."""

    nombre_seccion = 'Constantes Vitales'

    def construir(self, historial) -> List[Flowable]:
        cv = historial.constantes_vitales
        if not cv:
            return []

        elementos = self.encabezado_seccion('F. Constantes Vitales')

        filas = [
            ['Temperatura (°C)', 'Pulso (lpm)', 'Frec. Respiratoria', 'Presión Arterial'],
            [
                str(cv.temperatura or '—'),
                str(cv.pulso or '—'),
                str(cv.frecuencia_respiratoria or '—'),
                str(cv.presion_arterial or '—'),
            ],
        ]
        col_w = [ANCHO_PAGINA / 4] * 4
        t = Table(filas, colWidths=col_w)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_SECUNDARIO),
            ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
            ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0, 0), (-1, -1), 9),
            ('ALIGN',      (0, 0), (-1, -1), 'CENTER'),
            ('GRID',       (0, 0), (-1, -1), 0.3, COLOR_BORDE),
            ('TOPPADDING',    (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elementos.append(t)
        elementos.append(Spacer(1, 6))
        return elementos


# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 5 — ANTECEDENTES PERSONALES
# ═══════════════════════════════════════════════════════════════════════════════
class SeccionAntecedentesPersonales(BaseSeccion):
    """Antecedentes patológicos personales (sección D)."""

    nombre_seccion = 'Antecedentes Personales'

    def construir(self, historial) -> List[Flowable]:
        ap = historial.antecedentes_personales
        if not ap:
            return []

        elementos = self.encabezado_seccion('D. Antecedentes Personales')

        campos = [
            ('Alergias:', getattr(ap, 'alergias', None)),
            ('Enfermedades Sistémicas:', getattr(ap, 'enfermedades_sistemicas', None)),
            ('Medicamentos Actuales:', getattr(ap, 'medicamentos_actuales', None)),
            ('Cirugías Previas:', getattr(ap, 'cirugias_previas', None)),
            ('Hospitalizaciones:', getattr(ap, 'hospitalizaciones', None)),
            ('Observaciones:', getattr(ap, 'observaciones', None)),
        ]

        for etiqueta, valor in campos:
            if valor:
                elementos.append(self.fila_dato(etiqueta, valor))

        if len(elementos) == 1:  # solo encabezado
            return elementos + self.sin_datos()

        elementos.append(Spacer(1, 6))
        return elementos


# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 6 — ANTECEDENTES FAMILIARES
# ═══════════════════════════════════════════════════════════════════════════════
class SeccionAntecedentesFamiliares(BaseSeccion):
    """Antecedentes patológicos familiares (sección E)."""

    nombre_seccion = 'Antecedentes Familiares'

    def construir(self, historial) -> List[Flowable]:
        af = historial.antecedentes_familiares
        if not af:
            return []

        elementos = self.encabezado_seccion('E. Antecedentes Familiares')

        campos = [
            ('Diabetes:', getattr(af, 'diabetes', None)),
            ('Hipertensión:', getattr(af, 'hipertension', None)),
            ('Cardiopatías:', getattr(af, 'cardiopatias', None)),
            ('Cáncer:', getattr(af, 'cancer', None)),
            ('Observaciones:', getattr(af, 'observaciones', None)),
        ]

        for etiqueta, valor in campos:
            if valor:
                elementos.append(self.fila_dato(etiqueta, valor))

        if len(elementos) == 1:
            return elementos + self.sin_datos()

        elementos.append(Spacer(1, 6))
        return elementos


# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 7 — PLAN DE TRATAMIENTO
# ═══════════════════════════════════════════════════════════════════════════════
class SeccionPlanTratamiento(BaseSeccion):
    """Plan de tratamiento con sesiones consolidadas."""

    nombre_seccion = 'Plan de Tratamiento'

    def construir(self, historial) -> List[Flowable]:
        plan = historial.plan_tratamiento
        if not plan:
            return []

        elementos = self.encabezado_seccion('Plan de Tratamiento')

        # Datos del plan
        elementos.append(self.fila_dato('Título:', plan.titulo))
        elementos.append(self.fila_dato('Notas:', plan.notas_generales))
        elementos.append(Spacer(1, 4))

        # Sesiones
        sesiones = plan.sesiones.filter(activo=True).order_by('numero_sesion')

        if not sesiones.exists():
            elementos += self.sin_datos()
            return elementos

        encabezados = ['#', 'Fecha', 'Estado', 'Procedimientos', 'Observaciones']
        col_w = [12*mm, 28*mm, 25*mm, 65*mm, ANCHO_PAGINA - 130*mm]
        filas = []

        for s in sesiones:
            procs = s.procedimientos or []
            texto_procs = '; '.join(
                p.get('nombre', '') for p in procs[:3]
            ) + ('...' if len(procs) > 3 else '')

            filas.append([
                str(s.numero_sesion),
                str(s.fecha_programada or '—'),
                s.estado,
                texto_procs or '—',
                s.observaciones or s.notas or '—',
            ])

        t = self.tabla_datos(filas, encabezados, col_w)
        if t:
            elementos.append(t)

        elementos.append(Spacer(1, 6))
        return elementos


# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 8 — INDICADORES DE SALUD BUCAL
# ═══════════════════════════════════════════════════════════════════════════════
class SeccionIndicadoresSaludBucal(BaseSeccion):
    """Indicadores de salud bucal (placa, cálculo, gingivitis)."""

    nombre_seccion = 'Indicadores de Salud Bucal'

    def construir(self, historial) -> List[Flowable]:
        ind = historial.indicadores_salud_bucal
        if not ind:
            return []

        elementos = self.encabezado_seccion('Indicadores de Salud Bucal')

        campos = {k: v for k, v in vars(ind).items()
                  if not k.startswith('_') and k not in ('id', 'paciente_id', 'creado_por_id')}

        filas = []
        for campo, valor in campos.items():
            if valor not in (None, '', {}):
                filas.append([campo.replace('_', ' ').title(), str(valor)])

        if filas:
            t = self.tabla_datos(filas, col_widths=[80*mm, ANCHO_PAGINA - 80*mm])
            if t:
                elementos.append(t)
        else:
            elementos += self.sin_datos()

        elementos.append(Spacer(1, 6))
        return elementos


# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 9 — ÍNDICES DE CARIES (CPO/ceo)
# ═══════════════════════════════════════════════════════════════════════════════
class SeccionIndicesCaries(BaseSeccion):
    """Índices CPO/ceo del paciente."""

    nombre_seccion = 'Índices de Caries'

    def construir(self, historial) -> List[Flowable]:
        ic = historial.indices_caries
        if not ic:
            return []

        elementos = self.encabezado_seccion('Índices de Caries CPO / ceo')

        campos = [
            ('CPO Total:', getattr(ic, 'cpo_total', None)),
            ('C (Cariados):', getattr(ic, 'cariados', None)),
            ('P (Perdidos):', getattr(ic, 'perdidos', None)),
            ('O (Obturados):', getattr(ic, 'obturados', None)),
            ('ceo Total:', getattr(ic, 'ceo_total', None)),
            ('Observaciones:', getattr(ic, 'observaciones', None)),
        ]

        for etiqueta, valor in campos:
            if valor is not None:
                elementos.append(self.fila_dato(etiqueta, valor))

        elementos.append(Spacer(1, 6))
        return elementos


# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 10 — DIAGNÓSTICOS CIE-10
# ═══════════════════════════════════════════════════════════════════════════════
class SeccionDiagnosticosCIE(BaseSeccion):
    """Diagnósticos CIE-10 cargados en el historial."""

    nombre_seccion = 'Diagnósticos CIE-10'

    def construir(self, historial) -> List[Flowable]:
        if not historial.diagnosticos_cie_cargados:
            return []

        # Importación diferida para evitar dependencia circular
        try:
            from api.clinical_records.models.diagnostico_cie import DiagnosticoCIEHistorial
            diagnosticos = DiagnosticoCIEHistorial.objects.filter(
                historial_clinico=historial,
                activo=True,
            ).select_related('diagnostico_dental__codigo_cie')
        except Exception:
            return []

        if not diagnosticos.exists():
            return []

        elementos = self.encabezado_seccion('Diagnósticos CIE-10')

        encabezados = ['Código CIE', 'Descripción', 'Tipo', 'Pieza']
        col_w = [25*mm, 95*mm, 20*mm, 30*mm]
        filas = []

        for d in diagnosticos:
            dd = getattr(d, 'diagnostico_dental', None)
            codigo = getattr(getattr(dd, 'codigo_cie', None), 'codigo', '—') if dd else '—'
            descripcion = getattr(getattr(dd, 'codigo_cie', None), 'descripcion', '—') if dd else '—'
            pieza = getattr(dd, 'pieza_dental', '—') if dd else '—'
            filas.append([codigo, descripcion, d.tipo_cie, str(pieza)])

        t = self.tabla_datos(filas, encabezados, col_w)
        if t:
            elementos.append(t)

        elementos.append(Spacer(1, 6))
        return elementos


# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 11 — EXÁMENES COMPLEMENTARIOS
# ═══════════════════════════════════════════════════════════════════════════════
class SeccionExamenesComplementarios(BaseSeccion):
    """Exámenes complementarios solicitados e informados (sección L)."""

    nombre_seccion = 'Exámenes Complementarios'

    def construir(self, historial) -> List[Flowable]:
        ec = historial.examenes_complementarios
        if not ec:
            return []

        elementos = self.encabezado_seccion('L. Exámenes Complementarios')

        campos = [
            ('Pedido de Exámenes:', getattr(ec, 'pedido_examenes', None)),
            ('Detalle Pedido:', getattr(ec, 'pedido_examenes_detalle', None)),
            ('Informe:', getattr(ec, 'informe_examenes', None)),
            ('Detalle Informe:', getattr(ec, 'informe_examenes_detalle', None)),
            ('Estado:', getattr(ec, 'estado_examenes', None)),
        ]

        for etiqueta, valor in campos:
            if valor:
                elementos.append(self.fila_dato(etiqueta, valor))

        if len(elementos) == 1:
            return elementos + self.sin_datos()

        elementos.append(Spacer(1, 6))
        return elementos


# ═══════════════════════════════════════════════════════════════════════════════
# SECCIÓN 12 — OBSERVACIONES
# ═══════════════════════════════════════════════════════════════════════════════
class SeccionObservaciones(BaseSeccion):
    """Observaciones generales del odontólogo."""

    nombre_seccion = 'Observaciones'

    def construir(self, historial) -> List[Flowable]:
        if not historial.observaciones:
            return []

        elementos = self.encabezado_seccion('Observaciones del Profesional')
        elementos.append(self.fila_dato('', historial.observaciones))
        elementos.append(Spacer(1, 6))
        return elementos