# api/common/services/storage_service.py
"""
Factory Service que selecciona automáticamente el backend de storage correcto.
Implementa patrón Singleton para reutilizar la instancia.
"""
from django.conf import settings
from .storage_backend import StorageBackend, S3Backend, MinIOBackend
import logging

logger = logging.getLogger(__name__)


class StorageService:
    """
    Factory que instancia el backend correcto según configuración.
    Cambia entre MinIO (dev) y S3 (prod) con una variable de entorno.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._backend = cls._create_backend()
        return cls._instance
    
    @staticmethod
    def _create_backend() -> StorageBackend:
        """Crea el backend según STORAGE_BACKEND en settings"""
        backend_type = getattr(settings, 'STORAGE_BACKEND', 'minio')
        
        config = {
            'bucket_name': settings.AWS_STORAGE_BUCKET_NAME,
            'access_key': settings.AWS_ACCESS_KEY_ID,
            'secret_key': settings.AWS_SECRET_ACCESS_KEY,
        }
        
        if backend_type == 'minio':
            config['endpoint_url'] = settings.MINIO_ENDPOINT_URL
            logger.info(f" Usando MinIO local: {config['endpoint_url']}")
            return MinIOBackend(config)
        else:
            config['region'] = getattr(settings, 'AWS_S3_REGION_NAME', 'us-east-1')
            logger.info(f"  Usando AWS S3: {config['bucket_name']}")
            return S3Backend(config)
    
    def generate_upload_url(self, object_key: str, content_type: str, expiration: int = 300):
        """Genera URL prefirmada para subir archivo"""
        return self._backend.generate_upload_url(object_key, content_type, expiration)
    
    def generate_view_url(self, object_key: str, expiration: int = 3600, download_name=None):
        """Genera URL prefirmada para visualizar/descargar archivo"""
        return self._backend.generate_view_url(object_key, expiration, download_name)
    
    def check_file_exists(self, object_key: str) -> bool:
        """Verifica existencia del archivo"""
        return self._backend.check_file_exists(object_key)
    
    def delete_file(self, object_key: str) -> bool:
        """Elimina archivo del storage"""
        return self._backend.delete_file(object_key)
