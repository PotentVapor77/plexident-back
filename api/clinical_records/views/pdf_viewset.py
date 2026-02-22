# api/clinical_records/views/pdf_viewset.py
"""
Endpoints para generación de PDF del historial clínico.

FIX 406: El action generar_pdf ahora declara renderer_classes con un renderer
personalizado que acepta application/pdf. Sin esto, DRF hereda los renderers
del ViewSet (solo JSONRenderer), no puede satisfacer Accept: application/pdf
y devuelve 406 Not Acceptable.
"""
import logging

from django.http import HttpResponse
from rest_framework import renderers, status
from rest_framework.decorators import action
from rest_framework.response import Response

from api.clinical_records.models import ClinicalRecord
from api.clinical_records.services.pdf.clinical_record_pdf_builder import (
    ClinicalRecordPDFBuilder,
)

logger = logging.getLogger(__name__)


class PDFRenderer(renderers.BaseRenderer):
    """
    Renderer mínimo que le indica a DRF que este endpoint puede servir PDF.

    DRF usa renderer_classes para la negociación de contenido: si el cliente
    envía Accept: application/pdf y ningún renderer lo soporta → 406.
    Al declarar este renderer en el action, DRF acepta la petición y el método
    generar_pdf devuelve un HttpResponse directo (sin pasar por el renderer).
    """
    media_type = "application/pdf"
    format = "pdf"
    charset = None
    render_style = "binary"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        # Los bytes del PDF se devuelven directamente como HttpResponse,
        # por lo que este método nunca se invoca en la práctica.
        return data


class ClinicalRecordPDFMixin:
    """
    Mixin para añadir las acciones de PDF al ClinicalRecordViewSet.

    Uso:
        class ClinicalRecordViewSet(
            ClinicalRecordPDFMixin,
            ...
            viewsets.ModelViewSet,
        ):
    """

    # ─────────────────────────────────────────────────────────────────────────
    # GET /api/clinical-records/{id}/pdf/
    # GET /api/clinical-records/{id}/pdf/?secciones=datos_paciente,plan_tratamiento
    # ─────────────────────────────────────────────────────────────────────────
    @action(
        detail=True,
        methods=["get"],
        url_path="pdf",
        # FIX 406: declarar el renderer PDF aquí para que DRF acepte
        # Accept: application/pdf sin devolver 406 Not Acceptable.
        renderer_classes=[PDFRenderer],
    )
    def generar_pdf(self, request, pk=None):
        """
        Genera el PDF del historial clínico.

        Query params:
            secciones   Coma-separado. Si se omite, incluye todo.
                        Ejemplo: ?secciones=datos_paciente,constantes_vitales
            descarga    Si es "true" fuerza descarga; si no, abre en el browser.
                        Ejemplo: ?descarga=true
        """
        historial = self._get_historial_con_relaciones(pk)
        if historial is None:
            # Devolver JSON de error manualmente (el renderer es PDF)
            return HttpResponse(
                '{"detail": "Historial no encontrado"}',
                content_type="application/json",
                status=404,
            )

        # Secciones desde query param
        secciones_param = request.query_params.get("secciones", "").strip()
        secciones = (
            [s.strip() for s in secciones_param.split(",") if s.strip()]
            if secciones_param
            else None
        )

        try:
            pdf_bytes = ClinicalRecordPDFBuilder.generar(historial, secciones)
        except Exception as e:
            logger.error(
                f"Error generando PDF para historial {pk}: {e}",
                exc_info=True,
            )
            return HttpResponse(
                f'{{"detail": "Error al generar el PDF: {str(e)}"}}',
                content_type="application/json",
                status=500,
            )

        nombre_archivo = (
            f"HC_{historial.numero_historia_clinica_unica or pk}.pdf"
        )
        descarga = request.query_params.get("descarga", "false").lower() == "true"
        disposicion = "attachment" if descarga else "inline"

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'{disposicion}; filename="{nombre_archivo}"'
        )
        return response

    # ─────────────────────────────────────────────────────────────────────────
    # GET /api/clinical-records/pdf/secciones-disponibles/
    # ─────────────────────────────────────────────────────────────────────────
    @action(detail=False, methods=["get"], url_path="pdf/secciones-disponibles")
    def secciones_pdf_disponibles(self, request):
        """
        Retorna el catálogo de secciones disponibles para generar el PDF.
        """
        return Response({
            "secciones": ClinicalRecordPDFBuilder.secciones_disponibles(),
        })

    # ─────────────────────────────────────────────────────────────────────────
    # Helper privado
    # ─────────────────────────────────────────────────────────────────────────
    def _get_historial_con_relaciones(self, pk):
        """
        Obtiene el historial con todas las relaciones pre-cargadas
        para evitar N+1 queries durante la generación del PDF.
        """
        try:
            return (
                ClinicalRecord.objects
                .select_related(
                    "paciente",
                    "odontologo_responsable",
                    "constantes_vitales",
                    "antecedentes_personales",
                    "antecedentes_familiares",
                    "examen_estomatognatico",
                    "indicadores_salud_bucal",
                    "indices_caries",
                    "plan_tratamiento",
                    "plan_tratamiento__paciente",
                    "plan_tratamiento__creado_por",
                    "examenes_complementarios",
                )
                .prefetch_related(
                    "plan_tratamiento__sesiones",
                    "plan_tratamiento__sesiones__odontologo",
                )
                .get(pk=pk, activo=True)
            )
        except ClinicalRecord.DoesNotExist:
            return None