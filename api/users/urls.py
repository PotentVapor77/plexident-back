#api/users/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UsuarioViewSet, login_view

router = DefaultRouter()
router.register(r'', UsuarioViewSet, basename='users')  # ← AGREGAR basename


app_name = 'users' 
urlpatterns = [
    path('', include(router.urls)),

    path('auth/login/', login_view, name='login'),


]
