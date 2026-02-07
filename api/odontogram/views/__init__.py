# api/odontogram/views/__init__.py
"""
Inicializador del módulo views
Exporta todos los ViewSets y funciones API
"""

# ==================== CATÁLOGO VIEWSETS ====================
from .catalogo_views import (
    CategoriaDiagnosticoViewSet,
    DiagnosticoViewSet,
    AreaAfectadaViewSet,
    TipoAtributoClinicoViewSet,
    OdontogramaConfigViewSet,
)

# ==================== ODONTOGRAMA VIEWSETS ====================
from .odontograma_views import (
    PacienteViewSet,
    DienteViewSet,
    SuperficieDentalViewSet,
    DiagnosticoDentalViewSet,
    HistorialOdontogramaViewSet,
)

# ==================== FHIR VIEWSETS ====================
from .fhir_views import FHIRViewSet

# ==================== CUSTOM ENDPOINTS ====================
from .diagnostico_views import export_fhir_observation
from .cda_views import export_cda_xml, export_fhir_bundle

# ==================== INDICADORES ENDPOINTS ====================
from .indicadores_views import (
    obtener_informacion_piezas_indice,
    verificar_disponibilidad_piezas,
)

# ==================== EXPORTS ====================
__all__ = [
    # Catálogo ViewSets
    'CategoriaDiagnosticoViewSet',
    'DiagnosticoViewSet',
    'AreaAfectadaViewSet',
    'TipoAtributoClinicoViewSet',
    'OdontogramaConfigViewSet',
    'DiagnosticoCIEViewSet',
    
    # Odontograma ViewSets
    'PacienteViewSet',
    'DienteViewSet',
    'SuperficieDentalViewSet',
    'DiagnosticoDentalViewSet',
    'HistorialOdontogramaViewSet',
    
    # FHIR ViewSets
    'FHIRViewSet',
    
    # Custom endpoints
    'export_fhir_observation',
    'export_cda_xml',
    'export_fhir_bundle',
    
    # Indicadores endpoints
    'obtener_informacion_piezas_indice',
    'verificar_disponibilidad_piezas',
    
    
]
