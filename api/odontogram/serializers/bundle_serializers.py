# api/odontogram/serializers/bundle_serializer.py
from rest_framework import serializers
from datetime import datetime
from django.utils import timezone

from api.patients.models import Paciente
from api.odontogram.models import Diente, DiagnosticoDental, SuperficieDental
from api.odontogram.serializers.fhir_serializers import (
    FHIRPatientReferenceSerializer,
    BodyStructureFHIRSerializer,
    ClinicalFindingFHIRSerializer,
)
class FHIRBundleEntrySerializer(serializers.Serializer):
    """Estructura de una entrada en un Bundle FHIR"""
    fullUrl = serializers.CharField()
    resource = serializers.DictField()


class FHIRBundleSerializer(serializers.Serializer):
    """
    Serializador que genera un Bundle FHIR completo con:
    - Datos del paciente (Patient resource)
    - Estructuras anatómicas (BodyStructure resources)
    - Diagnósticos/Hallazgos (Condition/Procedure resources)
    
    Un Bundle es un contenedor FHIR que agrupa múltiples recursos.
    Esto es lo que exportas a sistemas externos.
    """
    
    resourceType = serializers.CharField(default="Bundle", read_only=True)
    type = serializers.CharField(default="searchset", read_only=True)
    timestamp = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    entry = serializers.SerializerMethodField()
    
    def get_timestamp(self, obj):
        """Timestamp del bundle"""
        return timezone.now().isoformat()
    
    def get_total(self, obj):
        """Número total de recursos en el bundle"""
        if not obj:
            return 0
        
        count = 1  # Patient
        
        if hasattr(obj, 'dientes'):
            for diente in obj.dientes.all():
                count += diente.superficies.count()  # BodyStructures
                for superficie in diente.superficies.all():
                    count += superficie.diagnosticos.count()  # Observations
        
        return count
    
    def get_entry(self, obj):
        """
        Genera todas las entradas del bundle.
        
        Estructura:
        1. Patient del odontograma
        2. BodyStructure por cada superficie dental
        3. Observation/Condition/Procedure por cada diagnóstico
        """
        if not obj:
            return []
        
        entries = []
        
        # 1. PATIENT RESOURCE
        patient_resource = self._generate_patient_resource(obj)
        entries.append({
            "fullUrl": f"urn:uuid:{obj.id}",
            "resource": patient_resource
        })
        
        # 2. BODY STRUCTURES (Dientes + Superficies)
        for diente in obj.dientes.all():
            for superficie in diente.superficies.all():
                body_structure_data = BodyStructureFHIRSerializer(superficie).data
                entries.append({
                    "fullUrl": f"urn:uuid:{superficie.id}",
                    "resource": body_structure_data
                })
        
        # 3. CLINICAL FINDINGS (Diagnósticos)
        for diente in obj.dientes.all():
            for superficie in diente.superficies.all():
                for diagnostico in superficie.diagnosticos.all():
                    clinical_finding_data = ClinicalFindingFHIRSerializer(diagnostico).data
                    entries.append({
                        "fullUrl": f"urn:uuid:{diagnostico.id}",
                        "resource": clinical_finding_data
                    })
        
        return entries
    
    def _generate_patient_resource(self, paciente):
        """
        Genera el recurso Patient FHIR desde un Paciente.
        """
        # Determinar género
        gender_map = {'M': 'male', 'F': 'female', 'O': 'other'}
        
        if hasattr(paciente, 'sexo'):
            gender = gender_map.get(
                paciente.sexo[0].upper() if paciente.sexo else 'O',
                'unknown'
            )
        else:
            gender = 'unknown'
        
        return {
            "resourceType": "Patient",
            "id": str(paciente.id),
            "identifier": [
                {   
                    "system": "urn:oid:plexident.co",
                    "value": str(paciente.id)
                }   
            ],
            "name": [
                {   
                    "use": "official",
                    "family": paciente.apellidos if paciente.apellidos else "",
                    "given": [paciente.nombres] if paciente.nombres else []
                }   
            ],
            "gender": gender,
            "birthDate": (
                paciente.fecha_nacimiento.isoformat()
                if hasattr(paciente, 'fecha_nacimiento') and paciente.fecha_nacimiento
                else None
            ),
            "contact": [
                {   
                    "telecom": [
                        {   
                            "system": "phone",
                            "value": paciente.telefono if hasattr(paciente, 'telefono') else None
                        },   
                        {   
                            "system": "email",
                            "value": paciente.email if hasattr(paciente, 'email') else None
                        }   
                    ]
                }   
            ]
        }


# ============================================================================
# EJEMPLO DE USO EN UN ENDPOINT
# ============================================================================

"""
Para exportar el bundle desde un endpoint (Temporal en lo que terminamos de arreglarlo todo):

views.py:
---------

from rest_framework.decorators import api_view
from rest_framework.response import Response

from api.odontogram.serializers.bundle_serializers import FHIRBundleSerializer
from api.patients.models import Paciente


@api_view(['GET'])
def export_fhir_bundle(request, paciente_id):
    \"\"\"Exporta odontograma como Bundle FHIR\"\"\"
    
    try:
        paciente = Paciente.objects.get(id=paciente_id)
    except Paciente.DoesNotExist:
        return Response({'error': 'Paciente no encontrado'}, status=404)
    
    serializer = FHIRBundleSerializer(paciente)
    return Response(serializer.data)


urls.py:
--------

from django.urls import path
from api.odontogram.views import export_fhir_bundle

urlpatterns = [
    path('api/fhir/bundle/<int:paciente_id>/', export_fhir_bundle, name='export_fhir_bundle'),
]
"""
