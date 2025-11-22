# api/odontogram/serializer/fhir_serializers.py

from rest_framework import serializers

from api.patients.models import Paciente
from api.odontogram.models import Diente, DiagnosticoDental, SuperficieDental

# =============================================================================
# NOTA: Estos serializadores son de SOLO LECTURA.
# Su propósito es transformar los datos de la base de datos de Plexident
# a formato JSON compatible con el estándar FHIR para interoperabilidad.
# =============================================================================


class FHIRPatientReferenceSerializer(serializers.ModelSerializer):
    """
    Serializador para representar una referencia simple a un Paciente en FHIR.
    """
    reference = serializers.SerializerMethodField()

    class Meta:
        model = Paciente
        fields = ['reference']

    def get_reference(self, obj):
        return f"Patient/{obj.id}"


class BodyStructureFHIRSerializer(serializers.ModelSerializer):
    """
    Serializador para transformar un modelo SuperficieDental en un recurso FHIR BodyStructure.
    Este recurso identifica de forma única la parte anatómica (diente y superficie).
    
    Documentación FHIR: https://www.hl7.org/fhir/bodystructure.html
    """
    resourceType = serializers.CharField(default="BodyStructure", read_only=True)
    
    # Identificador único para esta estructura anatómica
    identifier = serializers.SerializerMethodField()
    
    # Descripción textual de la ubicación
    description = serializers.SerializerMethodField()
    
    # Ubicación anatómica codificada
    location = serializers.SerializerMethodField()
    
    # Paciente al que pertenece esta estructura
    patient = FHIRPatientReferenceSerializer(source='diente.paciente', read_only=True)

    class Meta:
        model = SuperficieDental
        fields = [
            'resourceType',
            'id',
            'identifier',
            'description',
            'location',
            'patient',
        ]
        
    def get_identifier(self, obj):
        # Creamos un identificador único y persistente para esta superficie dental
        return [{
            "system": "urn:oid:plexident.co",
            "value": f"bodystructure-{obj.id}"
        }]

    def get_description(self, obj):
        return f"Superficie {obj.get_nombre_display()} del diente {obj.diente.codigo_fdi}"

    def get_location(self, obj):
        # Usamos el sistema de codificación FDI para dientes, que es común en odontología
        # y el código de superficie que ya teníamos mapeado.
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
                    "display": obj.get_nombre_display()
                }
            ],
            "text": self.get_description(obj)
        }


class FHIRPractitionerReferenceSerializer(serializers.Serializer):
    """
    Serializador para representar una referencia simple a un Practitioner (Odontólogo) en FHIR.
    Ej: "asserter": { "reference": "Practitioner/uuid-del-user" }
    """
    reference = serializers.SerializerMethodField()

    def get_reference(self, obj):
        return f"Practitioner/{obj.id}"

    def to_representation(self, instance):
        # El odontologo puede ser nulo, manejar ese caso
        if instance:
            return super().to_representation(instance)
        return None


class ClinicalFindingFHIRSerializer(serializers.ModelSerializer):
    """
    Serializador principal que transforma un DiagnosticoDental en un recurso clínico FHIR.
    Determina dinámicamente si el recurso debe ser una 'Condition' o un 'Procedure'
    basado en la clasificación del catálogo.
    """
    resourceType = serializers.SerializerMethodField()
    identifier = serializers.SerializerMethodField()
    
    # Mapeo de estado
    clinicalStatus = serializers.SerializerMethodField(method_name='get_condition_status') # Para Condition
    status = serializers.SerializerMethodField(method_name='get_procedure_status') # Para Procedure
    
    # Código del diagnóstico/procedimiento
    code = serializers.SerializerMethodField()
    
    # Paciente y ubicación anatómica
    subject = FHIRPatientReferenceSerializer(source='paciente', read_only=True)
    bodySite = serializers.SerializerMethodField()
    
    # Quién y cuándo lo registró
    asserter = FHIRPractitionerReferenceSerializer(source='odontologo', read_only=True) # Para Condition
    performer = serializers.SerializerMethodField() # Para Procedure
    recordedDate = serializers.DateTimeField(source='fecha', read_only=True)

    class Meta:
        model = DiagnosticoDental
        # Los campos se controlan dinámicamente en to_representation
        fields = [
            'resourceType',
            'id',
            'identifier',
            'clinicalStatus', # Condition
            'status', # Procedure
            'code',
            'subject',
            'bodySite',
            'asserter', # Condition
            'performer', # Procedure
            'recordedDate',
        ]
        
    def get_resourceType(self, obj):
        return obj.diagnostico_catalogo.tipo_recurso_fhir

    def get_identifier(self, obj):
        return [{
            "system": "urn:oid:plexident.co",
            "value": f"finding-{obj.id}"
        }]
        
    def _get_status_map(self):
        # Mapeo de estados internos a FHIR
        return {
            'diagnosticado': {"code": "active", "text": "Activo"},
            'en_tratamiento': {"code": "active", "text": "Activo"},
            'tratado': {"code": "resolved", "text": "Resuelto"},
            'cancelado': {"code": "inactive", "text": "Inactivo"},
        }
    
    def get_condition_status(self, obj):
        # http://hl7.org/fhir/valueset-condition-clinical.html
        fhir_status = self._get_status_map().get(obj.estado_tratamiento)
        if fhir_status:
            return {
                "coding": [{
                    "system": "http://terminology.hl7.org/CodeSystem/condition-clinical",
                    "code": fhir_status["code"],
                    "display": fhir_status["text"]
                }]
            }
        return None

    def get_procedure_status(self, obj):
        # http://hl7.org/fhir/valueset-event-status.html
        status_map = {
            'diagnosticado': 'preparation', # Se planea/prepara el procedimiento
            'en_tratamiento': 'in-progress',
            'tratado': 'completed',
            'cancelado': 'stopped'
        }
        return status_map.get(obj.estado_tratamiento, 'unknown')

    def get_code(self, obj):
        catalogo = obj.diagnostico_catalogo
        codings = []
        
        # Añadir código principal de Plexident/Formulario 033
        codings.append({
            "system": "urn:oid:plexident.co/diagnosis",
            "code": catalogo.key,
            "display": catalogo.nombre
        })
        
        if catalogo.codigo_fhir:
            codings.append({
                "system": "http://snomed.info/sct",
                "code": catalogo.codigo_fhir,
                "display": catalogo.nombre
            })
        if catalogo.codigo_icd10:
            codings.append({
                "system": "http://hl7.org/fhir/sid/icd-10",
                "code": catalogo.codigo_icd10
            })
        
        return {"coding": codings, "text": catalogo.nombre}

    def get_bodySite(self, obj):
        # Anidamos una representación simplificada de la superficie.
        # En un Bundle completo, esto sería una referencia a un recurso BodyStructure.
        superficie = obj.superficie
        diente = superficie.diente
        
        return [{
            "description": f"Superficie {superficie.get_nombre_display()} del diente {diente.codigo_fdi}",
            "identifier": {
                "system": "urn:oid:plexident.co",
                "value": f"bodystructure-{superficie.id}"
            }
        }]

    def get_performer(self, obj):
        if not obj.odontologo:
            return []
        return [{
            "actor": {
                "reference": f"Practitioner/{obj.odontologo.id}"
            }
        }]
    
    def to_representation(self, instance):
        """
        Controla dinámicamente los campos que se muestran según el resourceType.
        """
        data = super().to_representation(instance)
        resource_type = self.get_resourceType(instance)

        if resource_type == 'Condition':
            # Eliminar campos de Procedure
            del data['status']
            del data['performer']
        elif resource_type == 'Procedure':
            # Eliminar campos de Condition
            del data['clinicalStatus']
            del data['asserter']
        else: # Observation u otros
            del data['status']
            del data['performer']
            del data['clinicalStatus']
            del data['asserter']

        return data

