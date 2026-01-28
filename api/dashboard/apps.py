from django.apps import AppConfig

class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.dashboard'

    def ready(self):
        # Importa las señales cuando la aplicación se inicie
        import api.dashboard.signals
