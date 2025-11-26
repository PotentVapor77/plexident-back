# api/odontogram/views/cda_views.py
"""
ViewSets para exportación CDA (Clinical Document Architecture)
"""

import logging
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from api.odontogram.models import Paciente
from api.odontogram.generators.cda_generador import CDAOdontogramGenerator
from api.odontogram.serializers.bundle_serializers import FHIRBundleSerializer

logger = logging.getLogger(__name__)


# ==================== CDA EXPORT ENDPOINTS ====================


@api_view(['GET'])
def export_cda_xml(request, paciente_id):
    """
    Exporta el odontograma como documento CDA v3 XML.
    
    Endpoint: GET /api/odontogramas/{paciente_id}/export-cda/
    Response: XML documento CDA descargable
    
    Contiene:
    - Metadata del documento
    - Patient information
    - Odontograma section
    - Diagnósticos section
    - Plan de tratamiento section
    """
    try:
        paciente = Paciente.objects.get(id=paciente_id)
    except Paciente.DoesNotExist:
        return Response(
            {'error': 'Paciente no encontrado'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Obtener odontólogo del request (usuario logueado)
    odontologo = request.user if request.user.is_authenticated else None
    
    # Generar CDA
    generator = CDAOdontogramGenerator(paciente, odontologo)
    cda_xml = generator.generar_cda()
    
    # Retornar como archivo XML descargable
    response = HttpResponse(cda_xml, content_type='application/xml')
    filename = f"odontograma_{paciente.id}_{paciente.nombres.replace(' ', '_')}.xml"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


@api_view(['GET'])
def export_fhir_bundle(request, paciente_id):
    """
    Exporta el odontograma completo como Bundle FHIR R4.
    
    Endpoint: GET /api/odontogramas/{paciente_id}/export-fhir-bundle/
    Response: JSON con Bundle FHIR conteniendo:
    
    - Patient resource
    - BodyStructure resources (superficies)
    - Observation/Condition/Procedure resources (diagnósticos)
    """
    try:
        paciente = Paciente.objects.get(id=paciente_id)
    except Paciente.DoesNotExist:
        return Response(
            {'error': 'Paciente no encontrado'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    serializer = FHIRBundleSerializer(paciente)
    return Response(serializer.data, status=status.HTTP_200_OK)