# api/clinical_records/services/pdf/sections/seccion_n_diagnostico_cie.py
"""
Sección N del Formulario 033: DIAGNÓSTICO CIE

Muestra los diagnósticos CIE-10 cargados en el historial clínico,
con diseño de doble fila para evitar el desbordamiento de contenido largo.

Estructura de cada entrada (2 filas por diagnóstico):
  Fila 1: [Nº] [Diente FDI + Superficie]  [Código CIE]  [PRE ✓ / —]  [DEF ✓ / —]
  Fila 2: [colspan=5 → Nombre completo del diagnóstico en itálica]

Fuente de datos:
  historial.diagnosticos_cie.all()  →  DiagnosticoCIEHistorial
  Propiedades usadas:
    diag.nombre_diagnostico     → str
    diag.codigo_cie             → str  (ej: "K02.1")
    diag.diente_fdi             → str  (ej: "11")
    diag.tipo_cie               → "PRE" | "DEF"
    diag.diagnostico_dental.superficie.get_nombre_display()  → str
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
    ESTILOS,
)


# ═══════════════════════════════════════════════════════════════════════════
# PALETA DE COLORES (hereda de la base verde del formulario)
# ═══════════════════════════════════════════════════════════════════════════
VERDE_OSCURO    = COLOR_PRIMARIO       # encabezado sección
VERDE_CLARO     = COLOR_BORDE          # bordes de tabla
VERDE_MUY_CLARO = COLOR_ACENTO         # fila de nombre (segunda fila de cada par)
GRIS_HEADER     = colors.HexColor('#ECF0F1')
GRIS_TEXTO      = colors.HexColor('#2C3E50')
GRIS_ETIQUETA   = colors.HexColor('#5D6D7E')
BLANCO          = colors.white

AZUL_PRE        = colors.HexColor('#D4E6F1')   # fondo badge PRE
AZUL_PRE_TEXT   = colors.HexColor('#1A5276')   # texto badge PRE
VERDE_DEF       = colors.HexColor('#D5F5E3')   # fondo badge DEF
VERDE_DEF_TEXT  = colors.HexColor('#1E8449')   # texto badge DEF
GRIS_INACTIVO   = colors.HexColor('#F2F4F4')   # fondo marca vacía


# ═══════════════════════════════════════════════════════════════════════════
# ANCHOS DE COLUMNA  (ajustados a ANCHO_PAGINA ≈ 170 mm)
# Col: [ Nº | Diente/Superficie | Código CIE | PRE | DEF ]
# ═══════════════════════════════════════════════════════════════════════════
COL_NUM  = 10 * mm
COL_CIE  = 22 * mm
COL_PRE  = 18 * mm
COL_DEF  = 18 * mm
COL_DIENTE = ANCHO_PAGINA - COL_NUM - COL_CIE - COL_PRE - COL_DEF  # resto ≈ 102 mm
COL_WIDTHS = [COL_NUM, COL_DIENTE, COL_CIE, COL_PRE, COL_DEF]


# ═══════════════════════════════════════════════════════════════════════════
# ESTILOS LOCALES
# ═══════════════════════════════════════════════════════════════════════════
def _es(name, **kw) -> ParagraphStyle:
    """Factoría de estilos para evitar repetición."""
    defaults = dict(fontName='Helvetica', fontSize=8, textColor=GRIS_TEXTO, leading=10)
    defaults.update(kw)
    return ParagraphStyle(name, **defaults)


E_TITULO    = _es('N_titulo',  fontName='Helvetica-Bold', fontSize=11,
                  textColor=BLANCO, alignment=TA_CENTER, leading=13)
E_HEADER    = _es('N_hdr',    fontName='Helvetica-Bold', fontSize=8,
                  textColor=GRIS_ETIQUETA, alignment=TA_CENTER)
E_NUM       = _es('N_num',    fontName='Helvetica-Bold', fontSize=8,
                  textColor=GRIS_ETIQUETA, alignment=TA_CENTER)
E_DIENTE    = _es('N_diente', fontName='Helvetica-Bold', fontSize=9,
                  textColor=GRIS_TEXTO, alignment=TA_LEFT, leading=11)
E_CIE       = _es('N_cie',    fontName='Helvetica-Bold', fontSize=9,
                  textColor=colors.HexColor('#6C3483'), alignment=TA_CENTER, leading=11)
E_NOMBRE    = _es('N_nombre', fontName='Helvetica-Oblique', fontSize=8,
                  textColor=GRIS_ETIQUETA, alignment=TA_LEFT, leading=10)
E_PRE_ON    = _es('N_pre_on', fontName='Helvetica-Bold', fontSize=9,
                  textColor=AZUL_PRE_TEXT, alignment=TA_CENTER, leading=11)
E_DEF_ON    = _es('N_def_on', fontName='Helvetica-Bold', fontSize=9,
                  textColor=VERDE_DEF_TEXT, alignment=TA_CENTER, leading=11)
E_OFF       = _es('N_off',    fontName='Helvetica', fontSize=9,
                  textColor=colors.HexColor('#BDC3C7'), alignment=TA_CENTER, leading=11)
E_SIN_DATOS = _es('N_sin',    fontName='Helvetica-Oblique', fontSize=9,
                  textColor=GRIS_ETIQUETA, alignment=TA_CENTER, leading=12)
E_RESUMEN   = _es('N_res',    fontName='Helvetica', fontSize=8,
                  textColor=GRIS_ETIQUETA, alignment=TA_LEFT, leading=10)
E_RESUMEN_B = _es('N_resb',   fontName='Helvetica-Bold', fontSize=8,
                  textColor=GRIS_TEXTO, alignment=TA_LEFT, leading=10)


# ═══════════════════════════════════════════════════════════════════════════
# CLASE PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════
class SeccionNDiagnosticoCIE(BaseSeccion):
    """
    Sección N del Formulario 033: DIAGNÓSTICO CIE

    Lee los DiagnosticoCIEHistorial vinculados al historial clínico y los
    presenta en un formato de doble fila:
      • Fila superior: número de orden, diente + superficie, código CIE,
                       marcas PRE y DEF.
      • Fila inferior: nombre completo del diagnóstico en itálica, a ancho
                       completo (colspan 5), con fondo sutil para diferenciar.
    """

    @property
    def nombre_seccion(self) -> str:
        return 'N. Diagnóstico CIE'

    @property
    def es_opcional(self) -> bool:
        return True

    # ------------------------------------------------------------------
    # Punto de entrada público
    # ------------------------------------------------------------------
    def construir(self, historial) -> List[Flowable]:
        elementos: List[Flowable] = []

        elementos.append(self._encabezado_seccion())
        elementos.append(Spacer(1, 4))

        diagnosticos = self._obtener_diagnosticos(historial)

        if not diagnosticos:
            elementos.append(Paragraph(
                'No hay diagnósticos CIE registrados en este historial.',
                E_SIN_DATOS,
            ))
            elementos.append(Spacer(1, 8))
            return elementos

        elementos.append(self._tabla_diagnosticos(diagnosticos))
        elementos.append(Spacer(1, 5))
        elementos.append(self._barra_resumen(diagnosticos))
        elementos.append(Spacer(1, 8))
        return elementos

    # ------------------------------------------------------------------
    # Obtención de datos
    # ------------------------------------------------------------------
    @staticmethod
    def _obtener_diagnosticos(historial) -> list:
        """
        Obtiene los DiagnosticoCIEHistorial activos del historial.
        La relación inversa se llama 'diagnosticos_cie' según el servicio.
        """
        try:
            manager = getattr(historial, 'diagnosticos_cie', None)
            if manager is None:
                return []
            return list(
                manager.filter(activo=True)
                .select_related(
                    'diagnostico_dental',
                    'diagnostico_dental__diagnostico_catalogo',
                    'diagnostico_dental__superficie',
                    'diagnostico_dental__superficie__diente',
                )
                .order_by(
                    'diagnostico_dental__diagnostico_catalogo__nombre'
                )
            )
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Encabezado de sección
    # ------------------------------------------------------------------
    def _encabezado_seccion(self) -> Table:
        t = Table(
            [[Paragraph('N. DIAGNÓSTICO CIE', E_TITULO)]],
            colWidths=[ANCHO_PAGINA],
        )
        t.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, -1), VERDE_OSCURO),
            ('TOPPADDING',    (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        return t

    # ------------------------------------------------------------------
    # Tabla principal con doble fila por diagnóstico
    # ------------------------------------------------------------------
    def _tabla_diagnosticos(self, diagnosticos: list) -> Table:
        """
        Construye la tabla completa.

        Estructura por diagnóstico (2 filas):
          Fila A (datos):  Nº | Diente FDI – Superficie | CIE | PRE | DEF
          Fila B (nombre): colspan=5 → nombre completo en itálica
        """
        # ── Fila de encabezados de columna ──────────────────────────────
        fila_header = [
            Paragraph('Nº',         E_HEADER),
            Paragraph('Diente / Superficie', E_HEADER),
            Paragraph('CIE-10',     E_HEADER),
            Paragraph('PRE',        E_HEADER),
            Paragraph('DEF',        E_HEADER),
        ]

        filas: list = [fila_header]
        estilos_span: list = []  # comandos SPAN acumulados

        for idx, diag in enumerate(diagnosticos):
            # Índice de la fila A dentro de la tabla (0 = header)
            row_a = 1 + idx * 2   # fila de datos
            row_b = row_a + 1     # fila de nombre (segunda fila del par)

            # ── Extraer valores ────────────────────────────────────────
            nombre    = self._get_nombre(diag)
            codigo    = self._get_codigo_cie(diag)
            diente    = self._get_diente_superficie(diag)
            tipo_cie  = getattr(diag, 'tipo_cie', '') or ''

            # ── Fila A: datos principales ──────────────────────────────
            marca_pre, estilo_pre = self._marca(tipo_cie, 'PRE')
            marca_def, estilo_def = self._marca(tipo_cie, 'DEF')

            fila_a = [
                Paragraph(str(idx + 1),  E_NUM),
                Paragraph(diente,         E_DIENTE),
                Paragraph(codigo,         E_CIE),
                Paragraph(marca_pre,      estilo_pre),
                Paragraph(marca_def,      estilo_def),
            ]

            # ── Fila B: nombre completo (colspan 5) ───────────────────
            fila_b = [
                Paragraph(f'<i>{nombre}</i>', E_NOMBRE),
                '', '', '', '',   # celdas vacías para el span
            ]

            filas.append(fila_a)
            filas.append(fila_b)

            # Registrar SPAN para fila B
            estilos_span.append(('SPAN', (0, row_b), (4, row_b)))

        # ── Construir tabla ────────────────────────────────────────────
        tabla = Table(filas, colWidths=COL_WIDTHS, repeatRows=1)

        # Estilos base
        base_style = [
            # Encabezado
            ('BACKGROUND',    (0, 0), (-1, 0),  GRIS_HEADER),
            ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
            ('ALIGN',         (0, 0), (-1, 0),  'CENTER'),
            # Alineación general
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN',         (0, 1), (0, -1),  'CENTER'),  # col Nº
            ('ALIGN',         (2, 1), (4, -1),  'CENTER'),  # cols CIE/PRE/DEF
            # Bordes
            ('GRID',          (0, 0), (-1, -1), 0.5,  VERDE_CLARO),
            ('BOX',           (0, 0), (-1, -1), 1.0,  VERDE_CLARO),
            # Padding
            ('TOPPADDING',    (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING',   (0, 0), (-1, -1), 4),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 4),
        ]

        # Colorear filas B (nombre) con fondo sutil
        for idx in range(len(diagnosticos)):
            row_b = 2 + idx * 2
            base_style.append(
                ('BACKGROUND', (0, row_b), (-1, row_b), VERDE_MUY_CLARO)
            )
            # Borde inferior de la fila B más grueso → separa visualmente cada par
            base_style.append(
                ('LINEBELOW', (0, row_b), (-1, row_b), 1.0, VERDE_CLARO)
            )

        # Colorear marcas PRE/DEF según tipo
        for idx, diag in enumerate(diagnosticos):
            row_a = 1 + idx * 2
            tipo_cie = getattr(diag, 'tipo_cie', '') or ''
            if tipo_cie == 'PRE':
                base_style.append(('BACKGROUND', (3, row_a), (3, row_a), AZUL_PRE))
            elif tipo_cie == 'DEF':
                base_style.append(('BACKGROUND', (4, row_a), (4, row_a), VERDE_DEF))

        tabla.setStyle(TableStyle(base_style + estilos_span))
        return tabla

    # ------------------------------------------------------------------
    # Barra de resumen inferior
    # ------------------------------------------------------------------
    def _barra_resumen(self, diagnosticos: list) -> Table:
        total = len(diagnosticos)
        pre   = sum(1 for d in diagnosticos if (getattr(d, 'tipo_cie', '') or '') == 'PRE')
        defi  = sum(1 for d in diagnosticos if (getattr(d, 'tipo_cie', '') or '') == 'DEF')

        texto = (
            f'Total: <b>{total}</b> diagnóstico{"s" if total != 1 else ""}  │  '
            f'Presuntivos (PRE): <b>{pre}</b>  │  '
            f'Definitivos (DEF): <b>{defi}</b>'
        )

        t = Table(
            [[Paragraph(texto, E_RESUMEN)]],
            colWidths=[ANCHO_PAGINA],
        )
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

    # ------------------------------------------------------------------
    # Helpers de extracción y formato
    # ------------------------------------------------------------------
    @staticmethod
    def _get_nombre(diag) -> str:
        """Nombre legible del diagnóstico."""
        # Propiedad del modelo
        nombre = getattr(diag, 'nombre_diagnostico', None)
        if nombre:
            return nombre
        # Fallback a través de la relación
        try:
            return diag.diagnostico_dental.diagnostico_catalogo.nombre
        except AttributeError:
            return '—'

    @staticmethod
    def _get_codigo_cie(diag) -> str:
        """Código ICD-10 / CIE-10."""
        codigo = getattr(diag, 'codigo_cie', None)
        if codigo:
            return codigo
        try:
            return diag.diagnostico_dental.diagnostico_catalogo.codigo_icd10 or '—'
        except AttributeError:
            return '—'

    @staticmethod
    def _get_diente_superficie(diag) -> str:
        """
        Retorna texto 'FDI {fdi} — {superficie}'.
        Usa la propiedad diente_fdi si existe, luego navega la relación.
        """
        fdi = getattr(diag, 'diente_fdi', None)
        superficie = ''

        try:
            superficie = diag.diagnostico_dental.superficie.get_nombre_display()
        except AttributeError:
            pass

        if not fdi:
            try:
                fdi = diag.diagnostico_dental.superficie.diente.codigo_fdi
            except AttributeError:
                fdi = '—'

        if superficie:
            return f'FDI {fdi} — {superficie}'
        return f'FDI {fdi}'

    @staticmethod
    def _marca(tipo_cie: str, objetivo: str):
        """
        Retorna (texto, estilo) para la columna PRE o DEF.

        Si el tipo_cie coincide con objetivo → marca activa con checkmark.
        En caso contrario → guión en gris.
        """
        if tipo_cie == objetivo:
            texto  = '✓'
            estilo = E_PRE_ON if objetivo == 'PRE' else E_DEF_ON
        else:
            texto  = '—'
            estilo = E_OFF
        return texto, estilo

    # ------------------------------------------------------------------
    # Mensaje cuando no hay datos
    # ------------------------------------------------------------------
    def sin_datos(self) -> List[Flowable]:
        return [
            Paragraph(
                '<i>No hay diagnósticos CIE registrados en este historial</i>',
                ESTILOS['normal'],
            )
        ]


# ═══════════════════════════════════════════════════════════════════════════
# EXPORTACIÓN
# ═══════════════════════════════════════════════════════════════════════════
__all__ = ['SeccionNDiagnosticoCIE']