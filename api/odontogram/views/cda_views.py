# api/odontogram/views/cda_views.py

import logging

from django.http import HttpResponse
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status

from api.odontogram.models import Paciente
from api.odontogram.generators.cda_generador import CDAOdontogramGenerator
from api.odontogram.serializers.bundle_serializers import FHIRBundleSerializer

logger = logging.getLogger(__name__)

# ==================== CDA EXPORT ENDPOINTS ====================


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export_cda_xml(request, paciente_id):
    """
    Exporta el odontograma como documento CDA v3 XML.

    GET /api/odontogram/odontogramas/{paciente_id}/export-cda/

    Respuesta: archivo XML descargable.
    """
    try:
        paciente = Paciente.objects.get(id=paciente_id)
    except Paciente.DoesNotExist:
        # 404 estándar; lo envuelve el custom_exception_handler
        raise NotFound(detail="Paciente no encontrado")

    # Obtener odontólogo del request (usuario logueado)
    odontologo = request.user if request.user.is_authenticated else None

    # Generar CDA
    generator = CDAOdontogramGenerator(paciente, odontologo)
    cda_xml = generator.generar_cda()

    # Retornar como archivo XML descargable (aquí no interviene el renderer JSON)
    response = HttpResponse(cda_xml, content_type="application/xml")
    filename = f"odontograma_{paciente.id}_{paciente.nombres.replace(' ', '_')}.xml"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export_fhir_bundle(request, paciente_id):
    """
    Exporta el odontograma completo como Bundle FHIR R4.

    GET /api/odontogram/odontogramas/{paciente_id}/export-fhir-bundle/

    Respuesta: JSON con Bundle FHIR:
      - Patient
      - BodyStructure (superficies)
      - Observation/Condition/Procedure (diagnósticos)
    """
    try:
        paciente = Paciente.objects.get(id=paciente_id)
    except Paciente.DoesNotExist:
        raise NotFound(detail="Paciente no encontrado")

    serializer = FHIRBundleSerializer(paciente)
    # El StandardizedJSONRenderer envolverá esto en success/status_code/message/data/errors
    return Response(serializer.data, status=status.HTTP_200_OK)
