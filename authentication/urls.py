from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('me/', views.get_me, name='get_me'),
    path('refresh/', views.refresh_token_view, name='refresh_token'),  # ✅ NUEVO
    path('logout/', views.logout_view, name='logout'),
]
