# api/clinical_files/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ClinicalFileViewSet

router = DefaultRouter()
router.register(r'', ClinicalFileViewSet, basename='clinical-file') 

app_name = 'clinical_files'

urlpatterns = [
    path('', include(router.urls)),
]
