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

urlpatterns = [
    path('', include(router.urls)),
]