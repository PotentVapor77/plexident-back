from django.apps import AppConfig

class AuthenticationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'authentication'  # ← Solo esto porque está en raíz
    label = 'authentication'  # ← Label único
    verbose_name = 'Autenticación'

    def ready(self):
        """Conectar signals al iniciar app"""
        import authentication.signals  # ← Importa las señales