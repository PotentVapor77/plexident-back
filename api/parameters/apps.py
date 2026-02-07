# api/parameters/apps.py
from django.apps import AppConfig

class ParametersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.parameters'
    verbose_name = 'Parámetros del Sistema'
    
    def ready(self):
        # Importar señales si las necesitas
        # from . import signals
        pass