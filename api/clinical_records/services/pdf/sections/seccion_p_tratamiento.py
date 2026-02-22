# api/clinical_records/services/pdf/sections/seccion_p_tratamiento.py  [CORREGIDO]
"""
Sección P del Formulario 033: TRATAMIENTO

Columnas:
  No. DE SESIÓN Y FECHA | DIAGNÓSTICOS Y COMPLICACIONES | PROCEDIMIENTOS | PRESCRIPCIONES

CORRECCIONES:
  1. BUG CRÍTICO: _celda_lista devolvía list[Flowable].
     Una celda de Table solo acepta UN objeto Flowable — si recibe una lista Python,
     ReportLab la ignora silenciosamente y la celda aparece vacía.
     Solución: _lista_a_tabla() envuelve los Paragraphs en una Table de columna única.

  2. Campos reales de los dicts (confirmados desde el frontend PlanTratamientoSection.tsx):
       diagnosticos : 'diagnostico' | 'diagnostico_nombre' | 'nombre'
                      'diente', 'superficie' | 'superficie_nombre', 'tipo' | 'categoria'
       procedimientos: 'nombre' | 'descripcion', 'codigo', 'diente'
       prescripciones: 'medicamento', 'dosis', 'frecuencia', 'duracion'
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
    COLOR_BORDE,
    COLOR_ACENTO,
    ESTILOS,
)


# ═══════════════════════════════════════════════════════════════════════════
# PALETA
# ═══════════════════════════════════════════════════════════════════════════
VERDE_OSCURO    = COLOR_PRIMARIO
VERDE_CLARO     = COLOR_BORDE
VERDE_MUY_CLARO = COLOR_ACENTO
GRIS_HEADER     = colors.HexColor('#ECF0F1')
GRIS_TEXTO      = colors.HexColor('#2C3E50')
GRIS_ETIQUETA   = colors.HexColor('#5D6D7E')
BLANCO          = colors.white

ESTADO_BG = {
    'planificada': colors.HexColor('#EBF5FB'),
    'en_progreso': colors.HexColor('#FEF9E7'),
    'completada':  colors.HexColor('#EAFAF1'),
    'cancelada':   colors.HexColor('#FDEDEC'),
}
ESTADO_FG = {
    'planificada': colors.HexColor('#1A5276'),
    'en_progreso': colors.HexColor('#7D6608'),
    'completada':  colors.HexColor('#1E8449'),
    'cancelada':   colors.HexColor('#922B21'),
}
ESTADO_LABELS = {
    'planificada': 'PLANIFICADA',
    'en_progreso': 'EN PROGRESO',
    'completada':  'COMPLETADA',
    'cancelada':   'CANCELADA',
}


# ═══════════════════════════════════════════════════════════════════════════
# ANCHOS DE COLUMNA
# ═══════════════════════════════════════════════════════════════════════════
COL_SESION = 28 * mm
COL_DIAG   = (ANCHO_PAGINA - COL_SESION) * 0.34
COL_PROC   = (ANCHO_PAGINA - COL_SESION) * 0.36
COL_PRES   = ANCHO_PAGINA - COL_SESION - COL_DIAG - COL_PROC
COL_WIDTHS = [COL_SESION, COL_DIAG, COL_PROC, COL_PRES]


# ═══════════════════════════════════════════════════════════════════════════
# ESTILOS
# ═══════════════════════════════════════════════════════════════════════════
def _es(name, **kw) -> ParagraphStyle:
    defaults = dict(fontName='Helvetica', fontSize=8, textColor=GRIS_TEXTO, leading=10)
    defaults.update(kw)
    return ParagraphStyle(name, **defaults)


E_TITULO    = _es('P_tit',  fontName='Helvetica-Bold', fontSize=11,
                  textColor=BLANCO, alignment=TA_CENTER, leading=13)
E_HEADER    = _es('P_hdr',  fontName='Helvetica-Bold', fontSize=8,
                  textColor=GRIS_ETIQUETA, alignment=TA_CENTER)
E_SES_NUM   = _es('P_snum', fontName='Helvetica-Bold', fontSize=10,
                  textColor=GRIS_TEXTO, alignment=TA_CENTER, leading=12)
E_SES_FECHA = _es('P_sfec', fontName='Helvetica', fontSize=8,
                  textColor=GRIS_ETIQUETA, alignment=TA_CENTER, leading=10)
E_BULLET    = _es('P_bul',  fontName='Helvetica', fontSize=8,
                  textColor=GRIS_TEXTO, alignment=TA_LEFT, leading=11,
                  leftIndent=6, firstLineIndent=-6)
E_SECUNDARIO= _es('P_sec',  fontName='Helvetica', fontSize=7,
                  textColor=GRIS_ETIQUETA, alignment=TA_LEFT, leading=9,
                  leftIndent=12)
E_VACIO     = _es('P_bv',   fontName='Helvetica-Oblique', fontSize=8,
                  textColor=colors.HexColor('#BDC3C7'), alignment=TA_LEFT, leading=10)
E_SIN_DATOS = _es('P_sin',  fontName='Helvetica-Oblique', fontSize=9,
                  textColor=GRIS_ETIQUETA, alignment=TA_CENTER, leading=12)
E_RESUMEN   = _es('P_res',  fontName='Helvetica', fontSize=8,
                  textColor=GRIS_ETIQUETA, alignment=TA_LEFT, leading=10)


# ═══════════════════════════════════════════════════════════════════════════
# FUNCIÓN CLAVE: envolver lista de Paragraphs en una Table de columna única
# ═══════════════════════════════════════════════════════════════════════════
def _lista_a_tabla(flowables: list, ancho: float) -> Table:
    """
    Convierte una lista de Paragraph en un Table de una sola columna.

    POR QUÉ ES NECESARIO:
      Una celda de Table de ReportLab solo acepta UN objeto Flowable.
      Si se pasa una lista Python (list), ReportLab NO lanza error pero
      tampoco la renderiza — la celda queda en blanco silenciosamente.
      Esta función empaqueta todos los ítems en un Table contenedor,
      que sí es un único Flowable y que ReportLab puede renderizar.
    """
    if not flowables:
        return _lista_a_tabla([Paragraph('—', E_VACIO)], ancho)
    filas = [[f] for f in flowables]
    t = Table(filas, colWidths=[ancho])
    t.setStyle(TableStyle([
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ('TOPPADDING',    (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
        ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
    ]))
    return t


# ═══════════════════════════════════════════════════════════════════════════
# CLASE PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════
class SeccionPTratamiento(BaseSeccion):
    """Sección P del Formulario 033: TRATAMIENTO"""

    @property
    def nombre_seccion(self) -> str:
        return 'P. Tratamiento'

    @property
    def es_opcional(self) -> bool:
        return True

    def construir(self, historial) -> List[Flowable]:
        elementos: List[Flowable] = []
        elementos.append(self._encabezado_seccion())
        elementos.append(Spacer(1, 3))

        sesiones = self._obtener_sesiones(historial)

        if not sesiones:
            elementos.append(Paragraph(
                'No hay sesiones de tratamiento registradas en este historial.',
                E_SIN_DATOS,
            ))
            elementos.append(Spacer(1, 8))
            return elementos

        elementos.append(self._tabla_sesiones(sesiones))
        elementos.append(Spacer(1, 5))
        elementos.append(self._barra_resumen(sesiones))
        elementos.append(Spacer(1, 8))
        return elementos

    # ------------------------------------------------------------------
    # Obtención de datos
    # ------------------------------------------------------------------
    @staticmethod
    def _obtener_sesiones(historial) -> list:
        try:
            plan = getattr(historial, 'plan_tratamiento', None)
            if plan is None:
                return []
            manager = getattr(plan, 'sesiones', None)
            if manager is None:
                return []
            return list(
                manager.filter(activo=True)
                .select_related('odontologo')
                .order_by('numero_sesion')
            )
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Encabezado
    # ------------------------------------------------------------------
    def _encabezado_seccion(self) -> Table:
        t = Table(
            [[Paragraph('P. TRATAMIENTO', E_TITULO)]],
            colWidths=[ANCHO_PAGINA],
        )
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), VERDE_OSCURO),
            ('TOPPADDING',    (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        return t

    # ------------------------------------------------------------------
    # Tabla de sesiones
    # ------------------------------------------------------------------
    def _tabla_sesiones(self, sesiones: list) -> Table:
        fila_header = [
            Paragraph('No. SESIÓN\nY FECHA',            E_HEADER),
            Paragraph('DIAGNÓSTICOS\nY COMPLICACIONES', E_HEADER),
            Paragraph('PROCEDIMIENTOS',                 E_HEADER),
            Paragraph('PRESCRIPCIONES',                 E_HEADER),
        ]

        filas: list = [fila_header]
        estilos_extra: list = []

        for idx, sesion in enumerate(sesiones):
            row_idx = idx + 1

            # ── IMPORTANTE: cada celda debe ser UN objeto Flowable, no una lista ──
            filas.append([
                self._celda_sesion(sesion),
                self._celda_diagnosticos(
                    getattr(sesion, 'diagnosticos_complicaciones', None) or [],
                    COL_DIAG - 8 * mm,
                ),
                self._celda_procedimientos(
                    getattr(sesion, 'procedimientos', None) or [],
                    COL_PROC - 8 * mm,
                ),
                self._celda_prescripciones(
                    getattr(sesion, 'prescripciones', None) or [],
                    COL_PRES - 8 * mm,
                ),
            ])

            if idx % 2 == 1:
                estilos_extra.append(
                    ('BACKGROUND', (1, row_idx), (3, row_idx), VERDE_MUY_CLARO)
                )

        tabla = Table(filas, colWidths=COL_WIDTHS, repeatRows=1)
        base_style = [
            ('BACKGROUND',    (0, 0), (-1, 0),  GRIS_HEADER),
            ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
            ('ALIGN',         (0, 0), (-1, 0),  'CENTER'),
            ('BACKGROUND',    (0, 1), (0, -1),  VERDE_MUY_CLARO),
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
            ('GRID',          (0, 0), (-1, -1), 0.5,  VERDE_CLARO),
            ('BOX',           (0, 0), (-1, -1), 1.0,  VERDE_CLARO),
            ('LINEBELOW',     (0, 1), (-1, -1), 0.8,  VERDE_CLARO),
            ('TOPPADDING',    (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING',   (0, 0), (-1, -1), 4),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
        ]
        tabla.setStyle(TableStyle(base_style + estilos_extra))
        return tabla

    # ------------------------------------------------------------------
    # Celda sesión (col 0)
    # ------------------------------------------------------------------
    @staticmethod
    def _celda_sesion(sesion) -> Table:
        numero = f"#{sesion.numero_sesion}"

        fecha = getattr(sesion, 'fecha_realizacion', None) or getattr(sesion, 'fecha_programada', None)
        fecha_str = '—'
        if fecha:
            try:
                fecha_str = fecha.strftime('%d/%m/%Y')
            except AttributeError:
                fecha_str = str(fecha)[:10]

        estado_raw   = (getattr(sesion, 'estado', '') or '').lower()
        estado_label = ESTADO_LABELS.get(estado_raw, estado_raw.upper())
        color_bg     = ESTADO_BG.get(estado_raw, GRIS_HEADER)
        color_fg     = ESTADO_FG.get(estado_raw, GRIS_ETIQUETA)

        badge_style = ParagraphStyle(
            f'P_badge_{estado_raw}',
            fontName='Helvetica-Bold', fontSize=6,
            textColor=color_fg, alignment=TA_CENTER, leading=8,
        )
        badge = Table(
            [[Paragraph(estado_label, badge_style)]],
            colWidths=[COL_SESION - 8 * mm],
        )
        badge.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), color_bg),
            ('BOX',           (0, 0), (-1, -1), 0.5, color_fg),
            ('TOPPADDING',    (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING',   (0, 0), (-1, -1), 2),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 2),
        ]))
        c = Table(
            [
                [Paragraph(numero,    E_SES_NUM)],
                [Paragraph(fecha_str, E_SES_FECHA)],
                [badge],
            ],
            colWidths=[COL_SESION - 8 * mm],
        )
        c.setStyle(TableStyle([
            ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING',    (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
        ]))
        return c

    # ------------------------------------------------------------------
    # Celda diagnósticos (col 1)
    # Campos: 'diagnostico' | 'diagnostico_nombre' | 'nombre'
    #         'diente', 'superficie' | 'superficie_nombre', 'tipo' | 'categoria'
    # ------------------------------------------------------------------
    @classmethod
    def _celda_diagnosticos(cls, items: list, ancho: float) -> Table:
        if not items:
            return _lista_a_tabla([Paragraph('Sin diagnósticos registrados', E_VACIO)], ancho)

        flowables = []
        for item in items:
            if not isinstance(item, dict):
                flowables.append(Paragraph(f'• {item}', E_BULLET))
                continue

            nombre = (
                item.get('diagnostico') or
                item.get('diagnostico_nombre') or
                item.get('nombre') or '—'
            )
            flowables.append(Paragraph(f'• {nombre}', E_BULLET))

            partes_sec = []
            if item.get('diente'):
                partes_sec.append(f"FDI {item['diente']}")
            sup = item.get('superficie') or item.get('superficie_nombre')
            if sup:
                partes_sec.append(sup)
            tipo = item.get('tipo') or item.get('categoria')
            if tipo:
                partes_sec.append(tipo)
            if partes_sec:
                flowables.append(Paragraph('  ' + ' · '.join(partes_sec), E_SECUNDARIO))

        return _lista_a_tabla(flowables, ancho)

    # ------------------------------------------------------------------
    # Celda procedimientos (col 2)
    # Campos: 'nombre' | 'descripcion', 'codigo', 'diente'
    # ------------------------------------------------------------------
    @classmethod
    def _celda_procedimientos(cls, items: list, ancho: float) -> Table:
        if not items:
            return _lista_a_tabla([Paragraph('Sin procedimientos registrados', E_VACIO)], ancho)

        flowables = []
        for item in items:
            if not isinstance(item, dict):
                flowables.append(Paragraph(f'• {item}', E_BULLET))
                continue

            nombre = item.get('nombre') or item.get('descripcion') or '—'
            codigo = item.get('codigo')

            if codigo:
                linea = f'• <font color="#1A5276"><b>[{codigo}]</b></font> {nombre}'
            else:
                linea = f'• {nombre}'

            flowables.append(Paragraph(linea, E_BULLET))

            if item.get('diente'):
                flowables.append(Paragraph(f"  FDI {item['diente']}", E_SECUNDARIO))

        return _lista_a_tabla(flowables, ancho)

    # ------------------------------------------------------------------
    # Celda prescripciones (col 3)
    # Campos: 'medicamento', 'dosis', 'frecuencia', 'duracion'
    # ------------------------------------------------------------------
    @classmethod
    def _celda_prescripciones(cls, items: list, ancho: float) -> Table:
        if not items:
            return _lista_a_tabla([Paragraph('Sin prescripciones', E_VACIO)], ancho)

        flowables = []
        for item in items:
            if not isinstance(item, dict):
                flowables.append(Paragraph(f'• {item}', E_BULLET))
                continue

            medicamento = item.get('medicamento') or item.get('nombre') or '—'
            flowables.append(Paragraph(f'• {medicamento}', E_BULLET))

            partes = []
            if item.get('dosis'):
                partes.append(str(item['dosis']))
            if item.get('frecuencia'):
                partes.append(str(item['frecuencia']))
            if item.get('duracion'):
                partes.append(str(item['duracion']))
            if partes:
                flowables.append(Paragraph('  ' + ' · '.join(partes), E_SECUNDARIO))

        return _lista_a_tabla(flowables, ancho)

    # ------------------------------------------------------------------
    # Barra de resumen
    # ------------------------------------------------------------------
    @staticmethod
    def _barra_resumen(sesiones: list) -> Table:
        total       = len(sesiones)
        completadas = sum(1 for s in sesiones if (getattr(s, 'estado', '') or '').lower() == 'completada')
        planif      = sum(1 for s in sesiones if (getattr(s, 'estado', '') or '').lower() == 'planificada')
        en_prog     = sum(1 for s in sesiones if (getattr(s, 'estado', '') or '').lower() == 'en_progreso')
        canceladas  = sum(1 for s in sesiones if (getattr(s, 'estado', '') or '').lower() == 'cancelada')

        texto = (
            f'Total sesiones: <b>{total}</b>  │  '
            f'Completadas: <b>{completadas}</b>  │  '
            f'En progreso: <b>{en_prog}</b>  │  '
            f'Planificadas: <b>{planif}</b>  │  '
            f'Canceladas: <b>{canceladas}</b>'
        )
        t = Table([[Paragraph(texto, E_RESUMEN)]], colWidths=[ANCHO_PAGINA])
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), VERDE_MUY_CLARO),
            ('BOX',           (0, 0), (-1, -1), 0.5, VERDE_CLARO),
            ('TOPPADDING',    (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING',   (0, 0), (-1, -1), 6),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 6),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        return t

    def sin_datos(self) -> List[Flowable]:
        return [Paragraph(
            '<i>No hay tratamientos registrados en este historial</i>',
            ESTILOS['normal'],
        )]


__all__ = ['SeccionPTratamiento']