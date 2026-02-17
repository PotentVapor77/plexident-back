# api/clinical_records/services/pdf/sections/seccion_h_odontograma.py
"""
Sección H: Odontograma 2D
Lee la imagen PNG capturada desde el frontend e insertada en Form033Snapshot.
"""
import io
import logging
from typing import List

from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.enums import TA_CENTER

from api.clinical_records.services.pdf.sections.base_section import COLOR_BORDE, ESTILOS, BaseSeccion


logger = logging.getLogger(__name__)


class SeccionHOdontograma(BaseSeccion):
    """
    Inserta la imagen del odontograma 2D capturada desde el frontend.

    Prerrequisito:
        El snapshot Form033Snapshot asociado al historial debe tener el campo
        imagen_odontograma poblado (se envía automáticamente desde el frontend
        al guardar o refrescar el odontograma en modo "edit").
    """

    nombre_seccion = "H. ODONTOGRAMA 2D"

    def construir(self, historial) -> List:
        elementos = []
        elementos.append(self.titulo_seccion(self.nombre_seccion))

        try:
            snapshot = self._obtener_snapshot(historial)

            if snapshot and snapshot.imagen_odontograma:
                elementos.extend(self._insertar_imagen(snapshot))
            else:
                elementos.append(self._sin_datos())
        except Exception as exc:
            logger.error(
                "Error procesando odontograma para historial %s: %s",
                historial.id, exc, exc_info=True,
            )
            elementos.append(self._error())

        elementos.append(Spacer(1, 6))
        return elementos

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _obtener_snapshot(historial):
        """Retorna el Form033Snapshot del historial o None."""
        try:
            # Acceso por related_name definido en el modelo
            return getattr(historial, "form033_snapshot", None)
        except Exception as exc:
            logger.warning("No se pudo obtener snapshot: %s", exc)
            return None

    def _insertar_imagen(self, snapshot) -> List:
        """Inserta la imagen del odontograma centrada en el PDF."""
        elementos = []
        try:
            # Leer bytes de la imagen (funciona con FileField / ImageField)
            snapshot.imagen_odontograma.seek(0)
            imagen_bytes = snapshot.imagen_odontograma.read()

            img = Image(io.BytesIO(imagen_bytes))

            # Ajustar dimensiones conservando el aspect ratio
            ancho_max = 170 * mm
            alto_max  = 130 * mm
            ratio = min(ancho_max / img.drawWidth, alto_max / img.drawHeight)
            img.drawWidth  *= ratio
            img.drawHeight *= ratio

            # Centrar con tabla de 1 celda
            tabla = Table([[img]], colWidths=[ancho_max])
            tabla.setStyle(TableStyle([
                ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
                ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
                ("BOX",           (0, 0), (-1, -1), 0.5, COLOR_BORDE),
                ("TOPPADDING",    (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            elementos.append(tabla)

            # Nota de fecha de captura
            nota_style = ESTILOS["normal"].clone("NotaOdonto")
            nota_style.fontSize  = 7
            nota_style.alignment = TA_CENTER
            fecha = (
                snapshot.fecha_captura.strftime("%d/%m/%Y %H:%M")
                if snapshot.fecha_captura else "N/D"
            )
            elementos.append(Spacer(1, 3))
            elementos.append(
                Paragraph(f"<i>Odontograma capturado el {fecha}</i>", nota_style)
            )

        except Exception as exc:
            logger.error("Error insertando imagen del odontograma: %s", exc, exc_info=True)
            elementos.append(self._error())

        return elementos

    def _sin_datos(self):
        return Paragraph(
            "<i>No se ha capturado imagen del odontograma para este historial. "
            "Abra el historial en modo edición y guárdelo para generar la imagen automáticamente.</i>",
            ESTILOS["normal"],
        )

    def _error(self):
        return Paragraph(
            "<i>[Error al cargar la imagen del odontograma]</i>",
            ESTILOS["normal"],
        )