# api/parameters/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ConfiguracionHorarioViewSet,
    DiagnosticoViewSet,
    MedicamentoViewSet,
    ConfiguracionSeguridadViewSet,
    ConfiguracionNotificacionesViewSet,
    ParametroGeneralViewSet
)

router = DefaultRouter()
router.register(r'config-horarios', ConfiguracionHorarioViewSet, basename='config-horario')
router.register(r'diagnosticos', DiagnosticoViewSet, basename='diagnostico')
router.register(r'medicamentos', MedicamentoViewSet, basename='medicamento')
router.register(r'seguridad', ConfiguracionSeguridadViewSet, basename='seguridad')
router.register(r'notificaciones', ConfiguracionNotificacionesViewSet, basename='notificacion')
router.register(r'parametros-generales', ParametroGeneralViewSet, basename='parametro-general')

app_name = 'parameters'

urlpatterns = [
    path('', include(router.urls)),
    
    # Endpoints adicionales
    path('config-horarios/semana-actual/', ConfiguracionHorarioViewSet.as_view({'get': 'semana_actual'}), name='horarios-semana-actual'),
    path('config-horarios/verificar/', ConfiguracionHorarioViewSet.as_view({'get': 'verificar'}), name='horarios-verificar'),

    path('diagnosticos/categorias/', DiagnosticoViewSet.as_view({'get': 'categorias'}), name='diagnosticos-categorias'),
    path('medicamentos/categorias/', MedicamentoViewSet.as_view({'get': 'categorias'}), name='medicamentos-categorias'),
    
    path('medicamentos/vias/', MedicamentoViewSet.as_view({'get': 'vias_administracion'}), name='medicamentos-vias'),
    path('seguridad/validar-password/', ConfiguracionSeguridadViewSet.as_view({'get': 'validar_password'}), name='seguridad-validar-password'),
    path('notificaciones/probar/', ConfiguracionNotificacionesViewSet.as_view({'post': 'probar_recordatorio'}), name='notificaciones-probar'),
    path('parametros-generales/por-clave/', ParametroGeneralViewSet.as_view({'get': 'obtener_por_clave'}), name='parametros-por-clave'),
    path('parametros-generales/categorias/', ParametroGeneralViewSet.as_view({'get': 'categorias'}), name='parametros-categorias'),
]