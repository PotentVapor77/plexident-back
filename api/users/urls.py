#api/users/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import   PermisoUsuarioViewSet, UsuarioViewSet

router = DefaultRouter()
router.register(r'usuarios', UsuarioViewSet, basename='usuario')  # ←  basename
router.register(r"permisos-usuario", PermisoUsuarioViewSet, basename="permiso-usuario")  # Nuevo

app_name = 'users' #  Esto permite el namespace
urlpatterns = [
    path('', include(router.urls)),

]
