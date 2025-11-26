# api/odontogram/services/fhir_serializers.py
"""
Servicios reutilizables para operaciones FHIR
"""

from datetime import datetime
from api.odontogram.serializers.fhir_serializers import (
    FHIRPatientReferenceSerializer,
    ClinicalFindingFHIRSerializer,
    FHIRPractitionerReferenceSerializer,
)


class FHIRService:
    """Servicios para operaciones FHIR"""
    
    @staticmethod
    def crear_bundle_odontograma(paciente, diagnosticos):
        """
        Crea un FHIR Bundle tipo "collection" con odontograma completo
        
        Returns:
            dict: Bundle FHIR serializado
        """
        bundle = {
            'resourceType': 'Bundle',
            'type': 'collection',
            'timestamp': datetime.now().isoformat(),
            'total': 0,
            'entry': []
        }
        
        # 1. Patient
        patient_serializer = FHIRPatientReferenceSerializer(paciente)
        bundle['entry'].append({
            'fullUrl': f"Patient/{paciente.id}",
            'resource': patient_serializer.data,
            'search': {'mode': 'match'}
        })
        
        # 2. Diagnosticos (Conditions)
        for diag in diagnosticos:
            diag_serializer = ClinicalFindingFHIRSerializer(diag)
            bundle['entry'].append({
                'fullUrl': f"Condition/{diag.id}",
                'resource': diag_serializer.data,
                'search': {'mode': 'include'}
            })
        
        # 3. Odontólogo (Practitioner)
        if diagnosticos.exists():
            odontologist = diagnosticos.first().odontologo
            pract_serializer = FHIRPractitionerReferenceSerializer(odontologist)
            bundle['entry'].append({
                'fullUrl': f"Practitioner/{odontologist.id}",
                'resource': pract_serializer.data,
                'search': {'mode': 'include'}
            })
        
        bundle['total'] = len(bundle['entry'])
        return bundle
    
    @staticmethod
    def validar_recurso_fhir(resource, profile):
        """
        Valida un recurso FHIR contra su profile
        
        Returns:
            tuple: (valido: bool, issues: list[str])
        """
        from jsonschema import validate, ValidationError
        
        issues = []
        
        try:
            # Validaciones básicas
            if 'resourceType' not in resource:
                issues.append('Falta resourceType')
                return False, issues
            
            if 'id' not in resource:
                issues.append('Falta id del recurso')
                return False, issues
            # Por ahora validación básica
            
            return len(issues) == 0, issues
        
        except ValidationError as e:
            issues.append(str(e))
            return False, issues
    
    @staticmethod
    def buscar_recursos(patient_id=None, code=None, limit=10):
        """Busca recursos FHIR según criterios"""
        from api.odontogram.models import DiagnosticoDental
        
        query = DiagnosticoDental.objects.all()
        
        if patient_id:
            query = query.filter(superficie__diente__paciente_id=patient_id)
        
        if code:
            query = query.filter(codigo_fhir=code)
        
        results = []
        for diag in query[:limit]:
            from api.odontogram.serializers.fhir_serializers import ClinicalFindingFHIRSerializer
            serializer = ClinicalFindingFHIRSerializer(diag)
            results.append({
                'fullUrl': f"Condition/{diag.id}",
                'resource': serializer.data
            })
        
        return results