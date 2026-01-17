from django.apps import AppConfig


class ClinicalRecordsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api.clinical_records'
    verbose_name = 'Historiales Clínicos'

    def ready(self):
        import api.clinical_records.signals
