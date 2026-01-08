# api/appointment/apps.py
from django.apps import AppConfig


class AppointmentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.appointment'
    verbose_name = 'Gestión de Citas'
    
    def ready(self):
        """
        Importar signals cuando la app esté lista
        """
        import api.appointment.signals
