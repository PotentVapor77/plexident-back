from django.apps import AppConfig

class PatientsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.patients'

    def ready(self):
        # Importa las señales cuando la aplicación se inicie
        import api.patients.signals
