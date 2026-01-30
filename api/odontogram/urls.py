# api/odontogram/urls.py
"""
URLs completas para la API REST del Odontograma
Estructura: Catálogo + Instancias + FHIR + CDA
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

# ==================== IMPORTS VIEWSETS ====================

# Catálogo
from api.odontogram.views import (
    CategoriaDiagnosticoViewSet,
    DiagnosticoViewSet,
    AreaAfectadaViewSet,
    TipoAtributoClinicoViewSet,
    OdontogramaConfigViewSet,
)

# Instancias
from api.odontogram.views import (
    PacienteViewSet,
    DienteViewSet,
    SuperficieDentalViewSet,
    DiagnosticoDentalViewSet,
    HistorialOdontogramaViewSet,
)

# FHIR
from api.odontogram.views import FHIRViewSet

# Custom endpoints
from api.odontogram.views import (
    export_fhir_observation,
    export_cda_xml,
    export_fhir_bundle,
)

# Indicadores - Piezas Índice
from api.odontogram.views import (
    obtener_informacion_piezas_indice,
    verificar_disponibilidad_piezas,
)

# Formulario 033
from api.odontogram.views.form033_views import (
    obtener_form033_json,
    obtener_form033_html,
    descargar_form033_pdf,
    guardar_form033_pdf,
    listar_exports_form033,
    descargar_pdf_guardado,
)

# Odontograma views
from api.odontogram.views.odontograma_views import (
    IndicadoresSaludBucalListView,
    IndicadoresSaludBucalViewSet,
    OdontogramaCompletoView,
    guardar_odontograma_completo,
    obtener_definiciones_superficies,
)

from api.odontogram.views import plan_tratamiento_views

# ==================== ROUTER SETUP ====================

router = DefaultRouter()
router.register(
    r'planes-tratamiento',
    plan_tratamiento_views.PlanTratamientoViewSet,
    basename='plan-tratamiento'
)
router.register(
    r'sesiones-tratamiento',
    plan_tratamiento_views.SesionTratamientoViewSet,
    basename='sesion-tratamiento'
)

# CATÁLOGO (Lectura)
router.register(
    r"catalogo/categorias",
    CategoriaDiagnosticoViewSet,
    basename="categoria"
)

# GET /api/odontogram/catalogo/diagnosticos/
router.register(
    r"catalogo/diagnosticos",
    DiagnosticoViewSet,
    basename="diagnostico"
)

router.register(r"catalogo/areas", AreaAfectadaViewSet, basename="area")

# GET /api/odontogram/catalogo/atributos-clinicos/
router.register(
    r"catalogo/atributos-clinicos",
    TipoAtributoClinicoViewSet,
    basename="atributo-clinico"
)

# INSTANCIAS (CRUD)
router.register(r"pacientes", PacienteViewSet, basename="paciente")
router.register(r"dientes", DienteViewSet, basename="diente")
router.register(r"superficies", SuperficieDentalViewSet, basename="superficie")

router.register(
    r"diagnosticos-aplicados",
    DiagnosticoDentalViewSet,
    basename="diagnostico-aplicado"
)

router.register(r"historial", HistorialOdontogramaViewSet, basename="historial")

router.register(
    r"indicadores-salud-bucal",
    IndicadoresSaludBucalViewSet,
    basename="indicadores-salud-bucal",
)

# ==================== APP NAME ====================

app_name = "odontogram"

# ==================== URL PATTERNS ====================

urlpatterns = [
    # Router URLs
    path("", include(router.urls)),

    # ==================== INDICADORES - PIEZAS ÍNDICE ====================
    # IMPORTANTE: Estas rutas van primero para evitar conflictos
    
    # GET /api/odontogram/indicadores/piezas-indice/{paciente_id}/
    path(
        "indicadores/piezas-indice/<uuid:paciente_id>/",
        obtener_informacion_piezas_indice,
        name="piezas-indice-info",
    ),
    
    # GET /api/odontogram/indicadores/verificar-piezas/{paciente_id}/
    path(
        "indicadores/verificar-piezas/<uuid:paciente_id>/",
        verificar_disponibilidad_piezas,
        name="verificar-piezas-disponibilidad",
    ),

    # ==================== FHIR ENDPOINTS ====================
    
    # GET /api/odontogram/fhir/patient/{id}/
    path(
        "fhir/patient/<str:pk>/",
        FHIRViewSet.as_view({"get": "patient"}),
        name="fhir-patient",
    ),
    
    # GET /api/odontogram/fhir/odontograma/{paciente_id}/
    path(
        "fhir/odontograma/<str:paciente_id>/",
        FHIRViewSet.as_view({"get": "odontograma"}),
        name="fhir-odontograma",
    ),
    
    # GET /api/odontogram/fhir/cda/{paciente_id}/
    path(
        "fhir/cda/<str:paciente_id>/",
        FHIRViewSet.as_view({"get": "cda"}),
        name="fhir-cda",
    ),
    
    # POST /api/odontogram/fhir/validate/
    path(
        "fhir/validate/",
        FHIRViewSet.as_view({"post": "validate"}),
        name="fhir-validate",
    ),
    
    # GET /api/odontogram/fhir/search/
    path(
        "fhir/search/",
        FHIRViewSet.as_view({"get": "search"}),
        name="fhir-search",
    ),

    # ==================== CDA/EXPORT ENDPOINTS ====================
    
    # GET /api/odontogram/odontogramas/{paciente_id}/export-cda/
    path(
        "odontogramas/<str:paciente_id>/export-cda/",
        export_cda_xml,
        name="export-cda",
    ),
    
    # GET /api/odontogram/odontogramas/{paciente_id}/export-fhir-bundle/
    path(
        "odontogramas/<str:paciente_id>/export-fhir-bundle/",
        export_fhir_bundle,
        name="export-fhir-bundle",
    ),
    
    # GET /api/odontogram/diagnosticos/{diagnostico_id}/export-fhir/
    path(
        "diagnosticos/<str:diagnostico_id>/export-fhir/",
        export_fhir_observation,
        name="export-fhir-observation",
    ),

    # ==================== FORM 033 ENDPOINTS ====================
    
    # GET /api/odontogram/export/form033/{paciente_id}/json/
    path(
        "export/form033/<str:paciente_id>/json/",
        obtener_form033_json,
        name="form033-json",
    ),
    
    # GET /api/odontogram/export/form033/{paciente_id}/html/
    path(
        "export/form033/<str:paciente_id>/html/",
        obtener_form033_html,
        name="form033-html",
    ),
    
    # GET /api/odontogram/export/form033/{paciente_id}/pdf/
    path(
        "export/form033/<str:paciente_id>/pdf/",
        descargar_form033_pdf,
        name="form033-pdf",
    ),
    
    # POST /api/odontogram/export/form033/{paciente_id}/guardar-pdf/
    path(
        "export/form033/<str:paciente_id>/guardar-pdf/",
        guardar_form033_pdf,
        name="form033-guardar-pdf",
    ),
    
    # GET /api/odontogram/export/form033/exports/
    path(
        "export/form033/exports/",
        listar_exports_form033,
        name="form033-listar"
    ),
    
    # GET /api/odontogram/export/form033/descargar/{nombre_archivo}/
    path(
        "export/form033/descargar/<str:nombre_archivo>/",
        descargar_pdf_guardado,
        name="form033-descargar",
    ),

    # ==================== ODONTOGRAMA ENDPOINTS ====================
    
    # GET /api/odontogram/definiciones-superficies/
    path(
        'definiciones-superficies/',
        obtener_definiciones_superficies,
        name='definiciones-superficies'
    ),
    
    # POST /api/odontogram/pacientes/{paciente_id}/guardar-odontograma/
    path(
        "pacientes/<uuid:paciente_id>/guardar-odontograma/",
        guardar_odontograma_completo,
        name='guardar-odontograma-completo'
    ),
    
    # GET /api/odontogram/odontogramas/{paciente_id}/completo/
    path(
        "odontogramas/<uuid:paciente_id>/completo/",
        OdontogramaCompletoView.as_view(),
        name="odontograma-completo",
    ),
    
    # GET /api/odontogram/pacientes/{paciente_id}/indicadores/
    path(
        "pacientes/<uuid:paciente_id>/indicadores/",
        IndicadoresSaludBucalListView.as_view(),
        name="paciente-indicadores-list",
    ),
]
