# api/odontogram/views/diagnostico_views.py
"""
ViewSets para diagnósticos específicos (Custom Actions) y exportación FHIR
"""

import logging
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from api.odontogram.models import DiagnosticoDental, Paciente
from api.odontogram.serializers.fhir_serializers import ClinicalFindingFHIRSerializer

logger = logging.getLogger(__name__)


# ==================== DIAGNÓSTICO CUSTOM ENDPOINTS ====================


@api_view(['GET'])
def export_fhir_observation(request, diagnostico_id):
    """
    Exporta un diagnóstico individual como Observation FHIR.
    
    Endpoint: GET /api/diagnosticos/{diagnostico_id}/export-fhir/
    Response: JSON con un único recurso Observation/Condition/Procedure
    """
    try:
        diagnostico = DiagnosticoDental.objects.get(id=diagnostico_id)
    except DiagnosticoDental.DoesNotExist:
        return Response(
            {'error': 'Diagnóstico no encontrado'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = ClinicalFindingFHIRSerializer(diagnostico)
    return Response(serializer.data, status=status.HTTP_200_OK)