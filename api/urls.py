from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Crea el router y registra los endpoints
router = DefaultRouter()

# Define las rutas finales de la API
app_name = 'api'
urlpatterns = [
    path('', include(router.urls)),
    
]