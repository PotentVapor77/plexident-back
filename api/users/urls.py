#api/users/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UsuarioViewSet

router = DefaultRouter()
router.register(r'', UsuarioViewSet, basename='users')  # ←  basename


app_name = 'users' #  Esto permite el namespace
urlpatterns = [
    path('', include(router.urls)),

]
