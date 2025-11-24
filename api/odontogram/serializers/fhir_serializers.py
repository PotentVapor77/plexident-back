# api/odontogram/serializer/fhir_serializers.py

from rest_framework import serializers
from datetime import datetime
from django.utils import timezone

from api.patients.models import Paciente
from api.odontogram.models import Diente, DiagnosticoDental, SuperficieDental

# =============================================================================
# NOTA: Estos serializadores son de SOLO LECTURA.
# Su propósito es transformar los datos de la base de datos de Plexident
# a formato JSON compatible con el estándar FHIR para interoperabilidad.
# =============================================================================

class FHIRPatientReferenceSerializer(serializers.ModelSerializer):
    """
    Serializador para referencias a Paciente en FHIR.
    Retorna estructura completa compatible con R4/R5.
    """
    
    class Meta:
        model = Paciente
        fields = []
    
    def to_representation(self, instance):
        """Retorna referencia FHIR completa"""
        if not instance:
            return None
        
        return {
            "reference": f"Patient/{instance.id}",
            "type": "Patient",
            "identifier": {
                "system": "urn:oid:plexident.co",
                "value": str(instance.id)
            },
            "display": f"{instance.nombres} {instance.apellidos}".strip()
        }


class FHIRPractitionerReferenceSerializer(serializers.Serializer):
    """
    Serializador para referencias a Practitioner (Odontólogo) en FHIR.
    """
    
    def to_representation(self, instance):
        """Retorna referencia FHIR completa"""
        if not instance:
            return None
        
        return {
            "reference": f"Practitioner/{instance.id}",
            "type": "Practitioner",
            "identifier": {
                "system": "urn:oid:plexident.co",
                "value": str(instance.id)
            },
            "display": f"{instance.nombres} {instance.apellidos}".strip()
        }


# ============================================================================
# SERIALIZADOR DE ESTRUCTURA CORPORAL
# ============================================================================

class BodyStructureFHIRSerializer(serializers.ModelSerializer):
    """
    Serializador para transformar una superficie dental en un recurso
    BodyStructure de FHIR.
    """
    
    location = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    
    class Meta:
        model = SuperficieDental
        fields = ['location', 'description']
    
    def get_location(self, obj):
        """Retorna la ubicación anatómica del diente y superficie en FHIR"""
        return {
            "coding": [
                { 
                    "system": "http://terminology.hl7.org/CodeSystem/FDI-tooth-number",
                    "code": obj.diente.codigo_fdi,
                    "display": f"Diente {obj.diente.codigo_fdi}"
                }, 
                {  
                    "system": "http://terminology.hl7.org/CodeSystem/FDI-surface-codes",
                    "code": obj.codigo_fhir_superficie,
                    "display": obj.nombre  
                } 
            ],
            "text": self.get_description(obj)
        }
    
    def get_description(self, obj):
        """Descripción textual de la superficie"""
        return f"Superficie {obj.nombre} del diente {obj.diente.codigo_fdi}"
    
    def to_representation(self, instance):
        """Convierte la superficie a BodyStructure FHIR completo"""
        return {
            "resourceType": "BodyStructure",
            "id": str(instance.id),
            "identifier": [
                {  
                    "system": "urn:oid:plexident.co",
                    "value": str(instance.id)
                } 
            ],
            "active": True,
            "morphology": {
                "coding": [
                    {  
                        "system": "http://snomed.info/sct",
                        "code": "80106009",
                        "display": "Tooth structure"
                    }  
                ]
            },
            "location": self.get_location(instance),
            "description": self.get_description(instance)
        }


# ============================================================================
# SERIALIZADOR DE HALLAZGOS CLÍNICOS
# ============================================================================

class ClinicalFindingFHIRSerializer(serializers.ModelSerializer):
    """
    Serializador que transforma un DiagnosticoDental en un recurso FHIR.
    """
    
    resourceType = serializers.SerializerMethodField()
    id = serializers.CharField(read_only=True)
    identifier = serializers.SerializerMethodField()
    clinicalStatus = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    code = serializers.SerializerMethodField()
    subject = serializers.SerializerMethodField()
    bodySite = serializers.SerializerMethodField()
    performer = serializers.SerializerMethodField()
    asserter = serializers.SerializerMethodField()
    recordedDate = serializers.DateTimeField(source='fecha', read_only=True)
    onsetDateTime = serializers.SerializerMethodField()
    verificationStatus = serializers.SerializerMethodField()
    severity = serializers.SerializerMethodField()
    abatementDateTime = serializers.SerializerMethodField()
    component = serializers.SerializerMethodField()
    
    class Meta:
        model = DiagnosticoDental
        fields = [
            'resourceType',
            'id',
            'identifier',
            'clinicalStatus',
            'status',
            'code',
            'subject',
            'bodySite',
            'performer',
            'asserter',
            'recordedDate',
            'onsetDateTime',
            'verificationStatus',
            'severity',
            'abatementDateTime',
            'component',
        ]
    
    def get_resourceType(self, obj):
        """Determina el tipo de recurso basado en el tipo de diagnóstico"""
        if hasattr(obj.diagnostico_catalogo, 'tipo_recurso_fhir'):
            return obj.diagnostico_catalogo.tipo_recurso_fhir
        return "Observation"
    
    def get_identifier(self, obj):
        """Retorna identificadores únicos del diagnóstico"""
        return [
            {  
                "system": "urn:oid:plexident.co",
                "value": str(obj.id)
            }  
        ]
    
    def get_clinicalStatus(self, obj):
        """FHIR Condition: estado clínico del diagnóstico"""
        status_map = {
            'diagnosticado': 'active',
            'tratado': 'resolved',
            'cancelado': 'inactive',
        }
        
        status_code = status_map.get(obj.estado_tratamiento, 'active')
        return {
            "coding": [
                {  
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": status_code,
                    "display": status_code.capitalize()
                }  
            ]
        }
    
    def get_status(self, obj):
        """FHIR Procedure: estado de ejecución del procedimiento"""
        status_map = {
            'diagnosticado': 'in-progress',
            'tratado': 'completed',
            'cancelado': 'stopped',
        }
        
        status_code = status_map.get(obj.estado_tratamiento, 'in-progress')
        return status_code
    
    def get_code(self, obj):
        """Código del diagnóstico/procedimiento con SNOMED-CT e ICD-10-CM"""
        diagnostico = obj.diagnostico_catalogo
        return {
            "coding": [
                {  
                    "system": "http://snomed.info/sct",
                    "code": diagnostico.codigo_fhir or "unknown",
                    "display": diagnostico.nombre
                },  
                {  
                    "system": "http://hl7.org/fhir/sid/icd-10-cm",
                    "code": diagnostico.codigo_icd10 or "unknown",
                    "display": diagnostico.nombre
                }  
            ],
            "text": diagnostico.nombre
        }
    
    def get_subject(self, obj):
        """Referencia al paciente"""
        return FHIRPatientReferenceSerializer(
            obj.superficie.diente.paciente
        ).data
    
    def get_bodySite(self, obj):
        """Localización anatómica (diente + superficie)"""
        return {
            "coding": [
                { 
                    "system": "http://snomed.info/sct",
                    "code": f"FDI-{obj.superficie.diente.codigo_fdi}",
                    "display": f"Diente {obj.superficie.diente.codigo_fdi}"
                },  
                { 
                    "system": "http://terminology.hl7.org/CodeSystem/FDI-surface-codes",
                    "code": obj.superficie.codigo_fhir_superficie,
                    "display": obj.superficie.nombre  
                }  
            ]
        }
    
    def get_performer(self, obj):
        """Odontólogo que realiza el procedimiento"""
        if not obj.odontologo:
            return None
        return FHIRPractitionerReferenceSerializer(obj.odontologo).data
    
    def get_asserter(self, obj):
        """Quién afirma la condición (el odontólogo)"""
        if not obj.odontologo:
            return None
        return FHIRPractitionerReferenceSerializer(obj.odontologo).data
    
    def get_onsetDateTime(self, obj):
        """Cuándo empezó la condición (ISO 8601)"""
        return obj.fecha.isoformat() if obj.fecha else None
    
    def get_verificationStatus(self, obj):
        """Estado de verificación del diagnóstico"""
        return {
            "coding": [
                { 
                    "system": "http://terminology.hl7.org/CodeSystem/condition-ver-status",
                    "code": "confirmed",
                    "display": "Confirmado"
                }  
            ]
        }
    
    def get_severity(self, obj):
        """Mapea la prioridad del diagnóstico a severidad SNOMED-CT"""
        severity_map = {
            1: {
                "code": "24484000",
                "display": "Severa"
            },
            2: {
                "code": "371924009",
                "display": "Moderada"
            },
            3: {
                "code": "255604002",
                "display": "Leve"
            },
            4: {
                "code": "1148965001",
                "display": "Muy Leve"
            },
            5: {
                "code": "1148965001",
                "display": "Muy Leve"
            },
        }
        
        priority = getattr(obj.diagnostico_catalogo, 'prioridad', 3)
        severity_data = severity_map.get(priority, severity_map[3])
        
        return {
            "coding": [
                {  
                    "system": "http://snomed.info/sct",
                    "code": severity_data["code"],
                    "display": severity_data["display"]
                }  
            ]
        }
    
    def get_abatementDateTime(self, obj):
        """Retorna cuándo se resolvió la condición"""
        if obj.estado_tratamiento in ['tratado', 'cancelado']:
            return (obj.fecha_modificacion.isoformat()
                if obj.fecha_modificacion else None)
        return None
    
    def get_component(self, obj):
        """Retorna observaciones adicionales como components"""
        components = []
        
        # Movilidad dental (SNOMED-CT: 248488008 = Tooth mobility)
        if hasattr(obj, 'movilidad') and obj.movilidad is not None:
            components.append({
                "code": {
                    "coding": [
                        {  
                            "system": "http://snomed.info/sct",
                            "code": "248488008",
                            "display": "Tooth mobility"
                        } 
                    ]
                },
                "valueQuantity": {
                    "value": obj.movilidad,
                    "unit": "grade",
                    "system": "http://unitsofmeasure.org",
                    "code": "{grade}"
                }
            })
        
        # Recesión gingival (SNOMED-CT: 80106009 = Gingival recession)
        if hasattr(obj, 'recesion_gingival') and obj.recesion_gingival is not None:
            components.append({
                "code": {
                    "coding": [
                        {  
                            "system": "http://snomed.info/sct",
                            "code": "80106009",
                            "display": "Gingival recession"
                        } 
                    ]
                },
                "valueQuantity": {
                    "value": obj.recesion_gingival,
                    "unit": "mm",
                    "system": "http://unitsofmeasure.org",
                    "code": "mm"
                }
            })
        
        return components if components else None
    
    def to_representation(self, instance):
        """
        Controla dinámicamente los campos según el resourceType.
        Asegura que solo se incluyan campos válidos para cada tipo.
        """
        data = super().to_representation(instance)
        resource_type = self.get_resourceType(instance)
        
        fields_to_remove = []
        
        if resource_type == 'Condition':
            # Mantener campos de Condition, eliminar de Procedure/Observation
            fields_to_remove = ['status', 'performer']
        
        elif resource_type == 'Procedure':
            # Mantener campos de Procedure, eliminar de Condition
            fields_to_remove = [
                'clinicalStatus', 'asserter', 'verificationStatus',
                'severity', 'onsetDateTime', 'abatementDateTime'
            ]
        
        else:  # Observation u otros
            # Mantener solo lo común
            fields_to_remove = [
                'status', 'performer', 'clinicalStatus', 'asserter',
                'verificationStatus', 'severity', 'onsetDateTime', 'abatementDateTime'
            ]
        
        # FIX: Remover campos según resourceType
        for field in fields_to_remove:
            if field in data:
                del data[field]
        
        return data
