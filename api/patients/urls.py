# api/patients/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

#  CORREGIDO: from .views (relativo) en lugar de patients.views (absoluto)
from .views import AntecedentesFamiliaresViewSet, AntecedentesPersonalesViewSet, ConstantesVitalesViewSet, ExamenEstomatognaticoViewSet, PacienteViewSet

router = DefaultRouter()
router.register(r"pacientes", PacienteViewSet, basename="paciente")
# Descomenta cuando tengas los otros ViewSets
router.register(r"antecedentes-personales", AntecedentesPersonalesViewSet, basename="antecedentes-personales")
router.register(r"antecedentes-familiares", AntecedentesFamiliaresViewSet, basename="antecedentes-familiares")
router.register(r"constantes-vitales", ConstantesVitalesViewSet, basename="constantes-vitales")
router.register(r"examen-estomatognatico", ExamenEstomatognaticoViewSet, basename="examen-estomatognatico")

app_name = "patients"

urlpatterns = [
    path("", include(router.urls)),
]
