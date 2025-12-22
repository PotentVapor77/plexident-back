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

# Formulario 033
from api.odontogram.views.form033_views import (
    obtener_form033_json,
    obtener_form033_html,
    descargar_form033_pdf,
    guardar_form033_pdf,
    listar_exports_form033,
    descargar_pdf_guardado,
)


from api.odontogram.views.odontograma_views import obtener_definiciones_superficies
# ==================== ROUTER SETUP ====================

router = DefaultRouter()

# CATÁLOGO (Lectura)
router.register(
    r"catalogo/categorias", CategoriaDiagnosticoViewSet, basename="categoria"
)

router.register(r"catalogo/diagnosticos", DiagnosticoViewSet, basename="diagnostico")

router.register(r"catalogo/areas", AreaAfectadaViewSet, basename="area")

router.register(r"catalogo/atributos-clinicos", TipoAtributoClinicoViewSet, basename="atributo-clinico")

# INSTANCIAS (CRUD)
router.register(r"pacientes", PacienteViewSet, basename="paciente")

router.register(r"dientes", DienteViewSet, basename="diente")

router.register(r"superficies", SuperficieDentalViewSet, basename="superficie")

router.register(
    r"diagnosticos-aplicados", DiagnosticoDentalViewSet, basename="diagnostico-aplicado"
)

router.register(r"historial", HistorialOdontogramaViewSet, basename="historial")

# ==================== APP NAME ====================

app_name = "odontogram"

# ==================== URL PATTERNS ====================

urlpatterns = [
    # Router URLs
    path("", include(router.urls)),
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
    # Form 033 Endpoints
    path(
        "export/form033/<str:paciente_id>/json/",
        obtener_form033_json,
        name="form033-json",
    ),
    path(
        "export/form033/<str:paciente_id>/html/",
        obtener_form033_html,
        name="form033-html",
    ),
    path(
        "export/form033/<str:paciente_id>/pdf/",
        descargar_form033_pdf,
        name="form033-pdf",
    ),
    path(
        "export/form033/<str:paciente_id>/guardar-pdf/",
        guardar_form033_pdf,
        name="form033-guardar-pdf",
    ),
    path("export/form033/exports/", listar_exports_form033, name="form033-listar"),
    path(
        "export/form033/descargar/<str:nombre_archivo>/",
        descargar_pdf_guardado,
        name="form033-descargar",
    ),
    path(
        'definiciones-superficies/', 
        obtener_definiciones_superficies, 
        name='definiciones-superficies'
    ),
]


# ==================== ENDPOINT SUMMARY ====================

"""
ENDPOINTS DISPONIBLES:

=== CATÁLOGO (Lectura - GET) ===
GET  /api/odontogram/catalogo/categorias/
GET  /api/odontogram/catalogo/categorias/por_prioridad/?prioridad=ALTA
GET  /api/odontogram/catalogo/diagnosticos/
GET  /api/odontogram/catalogo/diagnosticos/{id}/
GET  /api/odontogram/catalogo/diagnosticos/por_categoria/?categoria_id=1
GET  /api/odontogram/catalogo/diagnosticos/criticos/
GET  /api/odontogram/catalogo/diagnosticos/buscar/?q=caries
GET  /api/odontogram/catalogo/areas/
GET  /api/odontogram/catalogo/atributos/

=== INSTANCIAS (CRUD) ===
GET    /api/odontogram/pacientes/
POST   /api/odontogram/pacientes/
GET    /api/odontogram/pacientes/{id}/
PUT    /api/odontogram/pacientes/{id}/
DELETE /api/odontogram/pacientes/{id}/
GET    /api/odontogram/pacientes/{id}/odontograma/
GET    /api/odontogram/pacientes/{id}/diagnosticos/
GET    /api/odontogram/pacientes/{id}/odontograma-fhir/

GET    /api/odontogram/dientes/
POST   /api/odontogram/dientes/
GET    /api/odontogram/dientes/{id}/
PUT    /api/odontogram/dientes/{id}/
DELETE /api/odontogram/dientes/{id}/
POST   /api/odontogram/dientes/{id}/marcar_ausente/

GET    /api/odontogram/superficies/
GET    /api/odontogram/diagnosticos-aplicados/
POST   /api/odontogram/diagnosticos-aplicados/
GET    /api/odontogram/diagnosticos-aplicados/{id}/
PUT    /api/odontogram/diagnosticos-aplicados/{id}/
DELETE /api/odontogram/diagnosticos-aplicados/{id}/
POST   /api/odontogram/diagnosticos-aplicados/{id}/marcar_tratado/
DELETE /api/odontogram/diagnosticos-aplicados/{id}/eliminar/

GET    /api/odontogram/historial/
GET    /api/odontogram/historial/{id}/

=== FHIR INTEROPERABILIDAD ===
GET    /api/odontogram/fhir/patient/{id}/
       → FHIR Patient Resource

GET    /api/odontogram/fhir/odontograma/{paciente_id}/
       → FHIR Bundle tipo "collection"

GET    /api/odontogram/fhir/cda/{paciente_id}/
       → CDA XML en FHIR Binary

POST   /api/odontogram/fhir/validate/
       → Validar recurso FHIR

GET    /api/odontogram/fhir/search/
       → Buscar recursos FHIR

=== EXPORTACIÓN CDA/FHIR ===
GET    /api/odontogram/odontogramas/{paciente_id}/export-cda/
       → XML descargable

GET    /api/odontogram/odontogramas/{paciente_id}/export-fhir-bundle/
       → JSON Bundle FHIR

GET    /api/odontogram/diagnosticos/{diagnostico_id}/export-fhir/
       → JSON Observation/Condition/Procedure FHIR
"""
