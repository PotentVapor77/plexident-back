from django.apps import AppConfig


class ClinicalFilesConfig(AppConfig):
    """
    Configuración de la aplicación de archivos clínicos.
    Gestiona archivos médicos almacenados en S3/MinIO.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.clinical_files'
    verbose_name = 'Archivos Clínicos'

    def ready(self):
        """
        Registra signals cuando la aplicación está lista.
        Implementa patrón Observer para eventos del modelo.
        """
        import api.clinical_files.signals  # noqa