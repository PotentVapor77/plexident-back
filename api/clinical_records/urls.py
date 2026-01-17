# api/clinical_records/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClinicalRecordViewSet

router = DefaultRouter()
router.register(r"", ClinicalRecordViewSet, basename="clinical-record")

urlpatterns = [
    path("", include(router.urls)),
]