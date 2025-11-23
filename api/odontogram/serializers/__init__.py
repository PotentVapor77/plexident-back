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
    
    # Se usan los nombres definidos:
    PacienteBasicSerializer,
    PacienteDetailSerializer,
    DienteDetailSerializer,
    SuperficieDentalListSerializer,
    DiagnosticoDentalListSerializer,
    DiagnosticoDentalDetailSerializer,
    DiagnosticoDentalCreateSerializer, # Incluir el serializer de creación si se usa
    
    HistorialOdontogramaSerializer,
    GuardarOdontogramaCompletoSerializer, # Serializer de la acción de guardar completo
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
    # Serializers genéricos (Solo nombres existentes)
    'CategoriaDiagnosticoSerializer',
    'DiagnosticoListSerializer',
    'DiagnosticoDetailSerializer',
    
    'AreaAfectadaSerializer',
    'TipoAtributoClinicoSerializer',
    'OpcionAtributoClinicoSerializer',
    'OdontogramaConfigSerializer',
    
    'PacienteBasicSerializer',           # Corregido
    'PacienteDetailSerializer',
    'DienteDetailSerializer',            # Corregido
    'SuperficieDentalListSerializer',    # Corregido
    'DiagnosticoDentalListSerializer',   # Corregido
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
]
