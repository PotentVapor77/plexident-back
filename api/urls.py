from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.odontogram.views import UserViewSet

# Crea el router y registra los endpoints
router = DefaultRouter()
router.register(r'users', UserViewSet)

# Define las rutas finales de la API
urlpatterns = [
    path('', include(router.urls)),
    path('api/odontogram/', include('api.odontogram.urls')),
]