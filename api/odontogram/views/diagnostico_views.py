# api/odontogram/views/diagnostico_views.py

"""
View para diagnósticos específicos (Custom Actions) y exportación FHIR
"""

import logging

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound

from api.odontogram.models import DiagnosticoDental
from api.odontogram.serializers.fhir_serializers import ClinicalFindingFHIRSerializer

logger = logging.getLogger(__name__)

# ==================== DIAGNÓSTICO CUSTOM ENDPOINTS ====================


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export_fhir_observation(request, diagnostico_id):
    """
    Exporta un diagnóstico individual como Observation/Condition/Procedure FHIR.

    Endpoint:
      GET /api/odontogram/diagnosticos/{diagnostico_id}/export-fhir/

    Response:
      JSON con un único recurso FHIR (Observation/Condition/Procedure)
    """
    try:
        diagnostico = DiagnosticoDental.objects.get(id=diagnostico_id)
    except DiagnosticoDental.DoesNotExist:
        # 404 estándar que tu custom_exception_handler formateará
        raise NotFound(detail="Diagnóstico no encontrado")

    serializer = ClinicalFindingFHIRSerializer(diagnostico)
    # El StandardizedJSONRenderer envolverá esta data en la estructura estándar
    return Response(serializer.data, status=status.HTTP_200_OK)
