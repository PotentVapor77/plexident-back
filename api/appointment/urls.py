# api/appointment/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CitaViewSet, HorarioAtencionViewSet, RecordatorioCitaViewSet

router = DefaultRouter()
router.register(r'citas', CitaViewSet, basename='cita')
router.register(r'horarios', HorarioAtencionViewSet, basename='horario-atencion')
router.register(r'recordatorios', RecordatorioCitaViewSet, basename='recordatorio')

app_name = "appointment"
urlpatterns = [
    path('', include(router.urls)),
]
