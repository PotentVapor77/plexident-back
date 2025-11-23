# odontogram/urls.py
"""
URLs para la API REST del Odontograma Alineado
Estructura: Catálogo + Instancias de Pacientes
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.odontogram.views import (
    # Catálogo
    CategoriaDiagnosticoViewSet,
    DiagnosticoViewSet,
    AreaAfectadaViewSet,
    TipoAtributoClinicoViewSet,
    OdontogramaConfigViewSet,
    # Instancias
    PacienteViewSet,
    DienteViewSet,
    DiagnosticoDentalViewSet,
    HistorialOdontogramaViewSet,
    SuperficieDentalViewSet,
    # Exportación FHIR
    export_fhir_bundle,
    export_cda_xml,
    export_fhir_observation,
    
)

router = DefaultRouter()

# Catálogo (diagnósticos, áreas, atributos)
router.register(r'catalogo/categorias', CategoriaDiagnosticoViewSet, basename='categoria')
router.register(r'catalogo/diagnosticos', DiagnosticoViewSet, basename='diagnostico')
router.register(r'catalogo/areas', AreaAfectadaViewSet, basename='area')
router.register(r'catalogo/atributos', TipoAtributoClinicoViewSet, basename='atributo')
router.register(r'catalogo/config', OdontogramaConfigViewSet, basename='config')

# Instancias de Pacientes
router.register(r'pacientes', PacienteViewSet, basename='paciente')
router.register(r'dientes', DienteViewSet, basename='diente')
router.register(r'superficies', SuperficieDentalViewSet, basename='superficie')
router.register(r'diagnosticos-aplicados', DiagnosticoDentalViewSet, basename='diagnostico-aplicado')
router.register(r'historial', HistorialOdontogramaViewSet, basename='historial')

app_name = 'odontogram'
urlpatterns = [
    # Rutas del router REST framework - ViewSets
    path('', include(router.urls)),
    # Exportación FHIR/CDA endpoints especiales
    path('pacientes/<uuid:paciente_id>/export-fhir-bundle/',
        export_fhir_bundle,
        name='export-fhir-bundle'),
    path('pacientes/<uuid:paciente_id>/export-cda/',
        export_cda_xml,
        name='export-cda'),
    path('diagnosticos/<uuid:diagnostico_id>/export-fhir/',
        export_fhir_observation,
        name='export-fhir-observation'),
]
    
    
