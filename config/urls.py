# config/urls.py
from django.contrib import admin
from django.urls import path, include


urlpatterns = [
    path("admin/", admin.site.urls),
    # Endpoints del sistema
    path("api/patients/", include("api.patients.urls", namespace="patients")),
    path("api/appointment/", include("api.appointment.urls", namespace="appointment")),
    path("api/auth/", include("authentication.urls")),
    path("api/users/", include("api.users.urls", namespace="users")),
    path("api/odontogram/", include("api.odontogram.urls")),
    path("api/clinical-records/", include("api.clinical_records.urls")),
    # Autenticación DRF (opcional, útil para pruebas)
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
]
