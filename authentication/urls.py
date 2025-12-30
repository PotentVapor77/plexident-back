from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('me/', views.get_me, name='get_me'),
    path('refresh/', views.refresh_token_view, name='refresh_token'),  
    path('logout/', views.logout_view, name='logout'),
    path('password-reset/', views.password_reset_view, name='password_reset'),
    path('password-reset-confirm/', views.password_reset_confirm_view, name='password_reset_confirm'),

]
