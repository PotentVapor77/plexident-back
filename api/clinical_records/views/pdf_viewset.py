# api/clinical_records/views/pdf_viewset.py
"""
Endpoints para generación de PDF del historial clínico.

Rutas disponibles:
    GET  /api/clinical-records/{id}/pdf/
         → PDF con todas las secciones

    GET  /api/clinical-records/{id}/pdf/?secciones=datos_paciente,constantes_vitales
         → PDF con secciones específicas

    GET  /api/clinical-records/pdf/secciones-disponibles/
         → Catálogo de secciones disponibles (para que el frontend
           pueda ofrecer al usuario qué secciones incluir)

Agregar al router en urls.py:
    router.register(r"", ClinicalRecordViewSet, basename="clinical-record")

Y añadir las acciones al ClinicalRecordViewSet copiando las funciones
de esta clase, o incluirlas como mixin.
"""
import logging

from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from api.clinical_records.models import ClinicalRecord
from api.clinical_records.services.pdf.clinical_record_pdf_builder import (
    ClinicalRecordPDFBuilder,
)

logger = logging.getLogger(__name__)


class ClinicalRecordPDFMixin:
    """
    Mixin para añadir las acciones de PDF al ClinicalRecordViewSet.

    Uso:
        class ClinicalRecordViewSet(
            ClinicalRecordPDFMixin,   # ← agregar aquí
            BasePermissionMixin,
            ...
            viewsets.ModelViewSet,
        ):
    """

    # ─────────────────────────────────────────────────────────────────────────
    # GET /api/clinical-records/{id}/pdf/
    # GET /api/clinical-records/{id}/pdf/?secciones=datos_paciente,plan_tratamiento
    # ─────────────────────────────────────────────────────────────────────────
    @action(detail=True, methods=['get'], url_path='pdf')
    def generar_pdf(self, request, pk=None):
        """
        Genera el PDF del historial clínico.

        Query params:
            secciones   Coma-separado. Si se omite, incluye todo.
                        Ejemplo: ?secciones=datos_paciente,constantes_vitales

            descarga    Si es "true" fuerza descarga; si no, abre en el browser.
                        Ejemplo: ?descarga=true

        Respuesta:
            application/pdf  con Content-Disposition apropiado.
        """
        historial = self._get_historial_con_relaciones(pk)
        if historial is None:
            return Response(
                {'detail': 'Historial no encontrado'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Secciones desde query param
        secciones_param = request.query_params.get('secciones', '').strip()
        secciones = (
            [s.strip() for s in secciones_param.split(',') if s.strip()]
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
            return Response(
                {'detail': f'Error al generar el PDF: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Nombre del archivo
        nombre_archivo = (
            f"HC_{historial.numero_historia_clinica_unica or pk}.pdf"
        )

        # inline (browser) o attachment (descarga)
        descarga = request.query_params.get('descarga', 'false').lower() == 'true'
        disposicion = 'attachment' if descarga else 'inline'

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'{disposicion}; filename="{nombre_archivo}"'
        )
        return response

    # ─────────────────────────────────────────────────────────────────────────
    # GET /api/clinical-records/pdf/secciones-disponibles/
    # ─────────────────────────────────────────────────────────────────────────
    @action(detail=False, methods=['get'], url_path='pdf/secciones-disponibles')
    def secciones_pdf_disponibles(self, request):
        """
        Retorna el catálogo de secciones disponibles para generar el PDF.

        Útil para que el frontend pueda ofrecer un selector de secciones.

        Respuesta:
        {
            "secciones": {
                "encabezado":              "Encabezado",
                "datos_paciente":          "Datos del Paciente",
                "constantes_vitales":      "Constantes Vitales",
                ...
            }
        }
        """
        return Response({
            'secciones': ClinicalRecordPDFBuilder.secciones_disponibles(),
        })

    # ─────────────────────────────────────────────────────────────────────────
    # Helper privado
    # ─────────────────────────────────────────────────────────────────────────
    def _get_historial_con_relaciones(self, pk):
        """
        Obtiene el historial con todas las relaciones necesarias pre-cargadas
        para evitar N+1 queries durante la generación del PDF.
        """
        try:
            return (
                ClinicalRecord.objects
                .select_related(
                    'paciente',
                    'odontologo_responsable',
                    'constantes_vitales',
                    'antecedentes_personales',
                    'antecedentes_familiares',
                    'examen_estomatognatico',
                    'indicadores_salud_bucal',
                    'indices_caries',
                    'plan_tratamiento',
                    'plan_tratamiento__paciente',
                    'plan_tratamiento__creado_por',
                    'examenes_complementarios',
                )
                .prefetch_related(
                    'plan_tratamiento__sesiones',
                    'plan_tratamiento__sesiones__odontologo',
                )
                .get(pk=pk, activo=True)
            )
        except ClinicalRecord.DoesNotExist:
            return None