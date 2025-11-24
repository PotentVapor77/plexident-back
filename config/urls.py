
# config/urls.py
from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path('admin/', admin.site.urls),


    # Endpoints del sistema
    path('api/patients/', include('api.patients.urls')),
    path('api/users/', include('api.users.urls')),
    path('api/odontogram/', include('api.odontogram.urls')),
    
    # Autenticación DRF (opcional, útil para pruebas)
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),

   

]
