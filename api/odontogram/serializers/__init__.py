# api/odontogram/serializers/__init__.py
# Serializers genéricos
from .serializers import (
    CategoriaDiagnosticoSerializer,
    DiagnosticoListSerializer,
    DiagnosticoDetailSerializer,
    AreaAfectadaSerializer,
    TipoAtributoClinicoSerializer,
    OpcionAtributoClinicoSerializer,
    OdontogramaConfigSerializer,
    IndicadoresSaludBucalSerializer, 
    
    PacienteBasicSerializer,
    # Se usan los nombres definidos:
    PacienteBasicSerializer,
    PacienteDetailSerializer,
    DienteDetailSerializer,
    SuperficieDentalListSerializer,
    DiagnosticoDentalListSerializer,
    DiagnosticoDentalDetailSerializer,
    DiagnosticoDentalCreateSerializer, 
    
    HistorialOdontogramaSerializer,
    GuardarOdontogramaCompletoSerializer, 
    
    IndiceCariesSnapshotSerializer,
    WritableIndiceCariesSnapshotSerializer,
    IndiceCariesSnapshotDetailSerializer
)

# Serializers FHIR
from .fhir_serializers import (
    FHIRPatientReferenceSerializer,
    FHIRPractitionerReferenceSerializer,
    BodyStructureFHIRSerializer,
    ClinicalFindingFHIRSerializer,
)

# Serializers Bundle FHIR
from .bundle_serializers import (
    FHIRBundleSerializer,
    FHIRBundleEntrySerializer,
)

# Exportar todos
__all__ = [
    # Serializers genéricos 
    'CategoriaDiagnosticoSerializer',
    'DiagnosticoListSerializer',
    'DiagnosticoDetailSerializer',
    
    'AreaAfectadaSerializer',
    'TipoAtributoClinicoSerializer',
    'OpcionAtributoClinicoSerializer',
    'OdontogramaConfigSerializer',
    
    'PacienteBasicSerializer',          
    'PacienteDetailSerializer',
    'DienteDetailSerializer',           
    'SuperficieDentalListSerializer',    
    'DiagnosticoDentalListSerializer',   
    'DiagnosticoDentalDetailSerializer',
    'DiagnosticoDentalCreateSerializer',
    
    'HistorialOdontogramaSerializer',
    'GuardarOdontogramaCompletoSerializer',
    
    # Serializers FHIR
    'FHIRPatientReferenceSerializer',
    'FHIRPractitionerReferenceSerializer',
    'BodyStructureFHIRSerializer',
    'ClinicalFindingFHIRSerializer',
    
    # Bundle FHIR
    'FHIRBundleSerializer',
    'FHIRBundleEntrySerializer',
    
    'IndicadoresSaludBucalSerializer', 
    'PacienteBasicSerializer',
    'IndiceCariesSnapshotSerializer',
    'WritableIndiceCariesSnapshotSerializer',
    'IndiceCariesSnapshotDetailSerializer',
]
