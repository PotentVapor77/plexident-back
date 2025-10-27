
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    #path('api/', include('api.urls')),  # Rutas del API (va a tu app)
    path('api/pacientes/', include('api.patients.urls')),
    path('api/usuarios/', include('api.users.urls')),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),  # login/logout DRF
    # API de usuarios - incluye todas las URLs de api.users

]
