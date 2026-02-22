# api/clinical_records/services/pdf/sections/seccion_h_odontograma.py
"""
Sección H: Odontograma 2D

Genera el odontograma directamente desde datos_form033 del Form033Snapshot,
sin almacenar ningún archivo (ni en disco ni en S3).

Flujo por solicitud de PDF (en orden de prioridad):
    1. Lee datos_form033 del Form033Snapshot asociado al historial.
    2. OdontogramaSVGGenerator construye el SVG vectorial en RAM.
    3a. [PREFERIDO]  svglib.svg2rlg + renderPDF  →  Drawing vectorial al PDF
                     100 % Python, SIN libcairo, funciona en Windows.
    3b. [FALLBACK 1] cairosvg / svglib+renderPM  →  PNG en RAM (requiere cairo).
    3c. [FALLBACK 2] Tabla textual con hallazgos resumidos.

Por qué 3a funciona sin cairo:
    svglib convierte el SVG a un objeto Drawing de reportlab.
    reportlab.graphics.renderPDF puede volcar ese Drawing directamente
    en el stream PDF sin pasar por ningún renderer de píxeles externo.
"""
import io
import logging
from typing import List

from reportlab.lib.units import mm
from reportlab.platypus import Flowable, Image, Paragraph, Spacer, Table, TableStyle

from api.clinical_records.services.pdf.sections.base_section import (
    COLOR_BORDE,
    ESTILOS,
    BaseSeccion,
)
from api.clinical_records.services.pdf.odontograma_svg_generator import (
    OdontogramaSVGGenerator,
)

logger = logging.getLogger(__name__)

ANCHO_MAX = 170 * mm
ALTO_MAX  = 130 * mm


# ─────────────────────────────────────────────────────────────────────────────
# Flowable puente: envuelve un Drawing de svglib y lo renderiza vectorialmente
# ─────────────────────────────────────────────────────────────────────────────

class _SVGDrawingFlowable(Flowable):
    """
    Flowable que incrusta un Drawing de reportlab (producido por svglib)
    directamente en el PDF como gráfico vectorial.

    No requiere cairo, Pillow ni ninguna DLL externa.
    """

    def __init__(self, drawing, target_width: float, target_height: float):
        super().__init__()
        self._drawing      = drawing
        self.width         = target_width
        self.height        = target_height
        self._scale_x      = target_width  / drawing.width
        self._scale_y      = target_height / drawing.height

    def draw(self):
        from reportlab.graphics import renderPDF  # noqa: PLC0415
        self.canv.saveState()
        self.canv.translate(0, 0)
        self.canv.scale(self._scale_x, self._scale_y)
        renderPDF.draw(self._drawing, self.canv, 0, 0)
        self.canv.restoreState()


# ─────────────────────────────────────────────────────────────────────────────
# Sección H - SOLO PERMANENTE
# ─────────────────────────────────────────────────────────────────────────────

class SeccionHOdontograma(BaseSeccion):

    nombre_seccion = "H. ODONTOGRAMA"

    # ── Punto de entrada ───────────────────────────────────────────────────

    def construir(self, historial) -> List[Flowable]:
        elementos: List[Flowable] = []
        elementos.extend(self.encabezado_seccion(self.nombre_seccion))

        try:
            snapshot = self._obtener_snapshot(historial)
            datos    = self._extraer_datos(snapshot)

            if datos:
                elementos.extend(self._renderizar(datos))
            else:
                elementos.append(self._sin_datos())

        except Exception as exc:
            logger.error(
                "Error construyendo sección odontograma (historial %s): %s",
                historial.id, exc, exc_info=True,
            )
            elementos.append(self._error())

        elementos.append(Spacer(1, 6))
        return elementos

    # ── Helpers privados ───────────────────────────────────────────────────

    @staticmethod
    def _obtener_snapshot(historial):
        try:
            return getattr(historial, "form033_snapshot", None)
        except Exception as exc:
            logger.warning("No se pudo acceder a form033_snapshot: %s", exc)
            return None

    @staticmethod
    def _extraer_datos(snapshot) -> dict | None:
        if snapshot is None:
            return None
        datos = getattr(snapshot, "datos_form033", None) or {}
        # Validación: debe tener al menos el arco permanente
        if not datos.get("odontograma_permanente"):
            return None
        return datos

    def _renderizar(self, datos: dict) -> List[Flowable]:
        """
        Intenta tres estrategias en orden:
          1. SVG → Drawing (svglib) insertado como vector en el PDF  [sin cairo]
          2. SVG → PNG (cairosvg / svglib+renderPM) insertado como imagen
          3. Tabla textual de hallazgos como último recurso
        """
        svg_str = OdontogramaSVGGenerator.generar_svg(datos)

        # ── Estrategia 1: vector directo (SIN cairo) ──────────────────────
        resultado = self._intentar_svg_vectorial(svg_str)
        if resultado is not None:
            return resultado

        # ── Estrategia 2: PNG vía cairo ───────────────────────────────────
        resultado = self._intentar_png(svg_str)
        if resultado is not None:
            return resultado

        # ── Estrategia 3: tabla textual ───────────────────────────────────
        logger.warning("Todas las estrategias de renderizado fallaron. Usando tabla textual.")
        return self._tabla_fallback(datos)

    # ── Estrategia 1: svglib → Drawing → PDF vectorial ────────────────────

    def _intentar_svg_vectorial(self, svg_str: str) -> List[Flowable] | None:
        """
        Usa svglib.svg2rlg para convertir el SVG a un Drawing de reportlab
        y lo incrusta directamente en el PDF usando renderPDF.draw().

        No necesita cairo, Pillow ni ninguna DLL del sistema operativo.
        Funciona en Windows, Linux y macOS con solo: pip install svglib
        """
        try:
            from svglib.svglib import svg2rlg  # type: ignore
        except ImportError:
            logger.info("svglib no está instalado — saltando estrategia vectorial.")
            return None

        try:
            svg_bytes = svg_str.encode("utf-8")
            drawing   = svg2rlg(io.BytesIO(svg_bytes))
            if drawing is None:
                logger.warning("svg2rlg devolvió None para el odontograma.")
                return None

            # Calcular dimensiones destino manteniendo aspect ratio
            ratio    = min(ANCHO_MAX / drawing.width, ALTO_MAX / drawing.height, 1.0)
            target_w = drawing.width  * ratio
            target_h = drawing.height * ratio

            flowable = _SVGDrawingFlowable(drawing, target_w, target_h)

            tabla = Table([[flowable]], colWidths=[ANCHO_MAX])
            tabla.setStyle(TableStyle([
                ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                ("BOX",           (0, 0), (-1, -1), 0.5, COLOR_BORDE),
                ("TOPPADDING",    (0, 0), (-1, -1), 6),  # Aumentado de 4 a 6
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),  # Aumentado de 4 a 6
            ]))

            logger.debug("Odontograma insertado como SVG vectorial (sin cairo).")
            return [tabla]

        except Exception as exc:
            logger.warning("Estrategia vectorial falló: %s", exc, exc_info=True)
            return None

    # ── Estrategia 2: PNG vía cairo ───────────────────────────────────────

    def _intentar_png(self, svg_str: str) -> List[Flowable] | None:
        """
        Convierte SVG → PNG usando cairosvg o svglib+renderPM.
        Requiere libcairo instalada en el OS.
        """
        try:
            png_bytes = OdontogramaSVGGenerator.svg_a_png(svg_str)
        except Exception as exc:
            logger.warning("SVG→PNG falló: %s", exc)
            return None

        try:
            from PIL import Image as PILImage  # noqa: PLC0415
            buf = io.BytesIO(png_bytes)
            with PILImage.open(buf) as pil_img:
                px_w, px_h = pil_img.size

            pts_w = px_w * (72.0 / 150.0)
            pts_h = px_h * (72.0 / 150.0)
            ratio = min(ANCHO_MAX / pts_w, ALTO_MAX / pts_h, 1.0)

            buf.seek(0)
            img = Image(buf, width=pts_w * ratio, height=pts_h * ratio)

            tabla = Table([[img]], colWidths=[ANCHO_MAX])
            tabla.setStyle(TableStyle([
                ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                ("BOX",           (0, 0), (-1, -1), 0.5, COLOR_BORDE),
                ("TOPPADDING",    (0, 0), (-1, -1), 6),  # Aumentado de 4 a 6
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),  # Aumentado de 4 a 6
            ]))

            logger.debug("Odontograma insertado como PNG.")
            return [tabla]

        except Exception as exc:
            logger.error("Error insertando PNG en el PDF: %s", exc, exc_info=True)
            return None

    # ── Estrategia 3: tabla textual de fallback ───────────────────────────

    def _tabla_fallback(self, datos: dict) -> List[Flowable]:
        """
        Representación tabular de hallazgos.
        Se usa únicamente si las estrategias 1 y 2 fallan.
        """
        from reportlab.lib import colors  # noqa: PLC0415

        elementos: List[Flowable] = []
        aviso = ESTILOS["normal"].clone("FallbackAviso")
        aviso.fontSize = 8
        elementos.append(Paragraph(
            "<i>[Imagen no disponible — se muestra resumen de hallazgos. "
            "Instala svglib (<code>pip install svglib</code>) para habilitar "
            "la imagen completa sin necesidad de libcairo.]</i>",
            aviso,
        ))
        elementos.append(Spacer(1, 4))

        hallazgos: list[tuple[str, str, str]] = []
        arco_key = "odontograma_permanente"  # Solo permanente
        for fila in (datos.get(arco_key) or {}).get("dientes", []):
            for d in fila:
                if d and d.get("simbolo"):
                    hallazgos.append((
                        d.get("codigo_fdi", "—"),
                        d.get("simbolo", ""),
                        d.get("descripcion", ""),
                    ))

        if hallazgos:
            tabla_data = [["FDI", "Símbolo", "Diagnóstico"]] + hallazgos[:30]
            t = Table(tabla_data, colWidths=[20 * mm, 20 * mm, 130 * mm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
                ("FONTSIZE",   (0, 0), (-1, -1), 7),
                ("GRID",       (0, 0), (-1, -1), 0.3, colors.HexColor("#CBD5E0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                 [colors.white, colors.HexColor("#F7FAFC")]),
            ]))
            elementos.append(t)
        else:
            elementos.append(self._sin_datos())

        return elementos

    # ── Mensajes vacío / error ─────────────────────────────────────────────

    def _sin_datos(self) -> Flowable:
        return Paragraph(
            "<i>No hay datos de odontograma registrados para este historial.</i>",
            ESTILOS["normal"],
        )

    def _error(self) -> Flowable:
        return Paragraph(
            "<i>[Error al generar la sección de odontograma]</i>",
            ESTILOS["normal"],
        )