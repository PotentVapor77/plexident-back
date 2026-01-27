# api/dashboard/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from api.dashboard.views import DashboardViewSet

router = DefaultRouter()
router.register(r"", DashboardViewSet, basename="dashboard")

app_name = "dashboard"

# URLs personalizadas para las acciones @action
urlpatterns = [
    path("", include(router.urls)),
    
    # ✅ URLs para las acciones personalizadas del dashboard
    path(
        "stats/",
        DashboardViewSet.as_view({'get': 'stats'}),
        name="dashboard-stats"
    ),
    path(
        "overview/",
        DashboardViewSet.as_view({'get': 'overview'}),
        name="dashboard-overview"
    ),
    path(
        "citas-stats/",
        DashboardViewSet.as_view({'get': 'citas_stats'}),
        name="dashboard-citas-stats"
    ),
    path(
        "periodos-disponibles/",
        DashboardViewSet.as_view({'get': 'periodos_disponibles'}),
        name="dashboard-periodos-disponibles"
    ),
    path(
        "kpis/",
        DashboardViewSet.as_view({'get': 'kpis'}),
        name="dashboard-kpis"
    ),
    # ✅ RF-06.3: Diagnósticos frecuentes
    path(
        "diagnosticos-frecuentes/",
        DashboardViewSet.as_view({'get': 'diagnosticos_frecuentes'}),
        name="dashboard-diagnosticos-frecuentes"
    ),
    # ✅ RF-06.5: Estadísticas Índice Caries
    path(
        "estadisticas-indice-caries/",
        DashboardViewSet.as_view({'get': 'estadisticas_indice_caries'}),
        name="dashboard-estadisticas-indice-caries"
    ),
    path(
        "evolucion-indice-caries/",
        DashboardViewSet.as_view({'get': 'evolucion_indice_caries'}),
        name="dashboard-evolucion-indice-caries"
    ),
    # ✅ RF-06.3 + RF-06.5: Estadísticas avanzadas
    path(
        "estadisticas-avanzadas/",
        DashboardViewSet.as_view({'get': 'estadisticas_avanzadas'}),
        name="dashboard-estadisticas-avanzadas"
    ),
]