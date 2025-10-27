from django.apps import AppConfig

class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.users'

    def ready(self):
        # Importa las señales cuando la aplicación se inicie
        import api.users.signals
