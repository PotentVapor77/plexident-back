# odontogram/urls.py
"""Rutas para la API REST del sistema de odontogramas extensible."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoriaDiagnosticoViewSet,
    DiagnosticoViewSet,
    AreaAfectadaViewSet,
    TipoAtributoClinicoViewSet,
    OdontogramaConfigViewSet,
)

router = DefaultRouter()
router.register(r'categorias', CategoriaDiagnosticoViewSet, basename='categoria')
router.register(r'diagnosticos', DiagnosticoViewSet, basename='diagnostico')
router.register(r'areas', AreaAfectadaViewSet, basename='area')
router.register(r'atributos', TipoAtributoClinicoViewSet, basename='atributo')
router.register(r'odontograma', OdontogramaConfigViewSet, basename='odontograma')

urlpatterns = [
    path('', include(router.urls)),
]