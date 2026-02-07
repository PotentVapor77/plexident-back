# api/clinical_records/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from api.clinical_records.views.oral_health_indicators_viewset import OralHealthIndicatorsViewSet
from .views import ClinicalRecordViewSet

router = DefaultRouter()
router.register(r"", ClinicalRecordViewSet, basename="clinical-record")

urlpatterns = [
    path("", include(router.urls)),
    # Ruta directa para validar piezas
    path(
        'validar-piezas-indicadores/<uuid:paciente_id>/',
        OralHealthIndicatorsViewSet.as_view({'get': 'validar_piezas_indicadores'}),
        name='validar-piezas-indicadores'
    ),
]