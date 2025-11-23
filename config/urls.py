
# config/urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


urlpatterns = [
    path('admin/', admin.site.urls),


    # Endpoints del sistema
    path('api/patients/', include('api.patients.urls')),
    path('api/users/', include('api.users.urls')),
    path('api/odontogram/', include('api.odontogram.urls')),
    
    # Autenticación DRF (opcional, útil para pruebas)
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),

    # JWT endpoints
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

]
