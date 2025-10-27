from django.apps import AppConfig

class OdontogramConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.odontogram'
    verbose_name = "Sistema de Odontograma"

    def ready(self):
        # Importa las señales cuando la aplicación se inicie
        import api.odontogram.signals
        print("Sistema de Odontograma inicializado")
        print("Signals (Observer Pattern) registrados")
