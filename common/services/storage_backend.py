# api/common/services/storage_backend.py
"""
Implementación del patrón Strategy para backends de almacenamiento.
Permite cambiar entre MinIO (desarrollo) y AWS S3 (producción) sin modificar código.
"""
from abc import ABC, abstractmethod
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Interfaz abstracta para backends de almacenamiento compatible S3"""
    
    @abstractmethod
    def generate_upload_url(self, object_key: str, content_type: str, expiration: int = 300) -> Optional[str]:
        """Genera URL prefirmada para subir archivo (PUT)"""
        pass
    
    @abstractmethod
    def generate_view_url(self, object_key: str, expiration: int = 3600, download_name: Optional[str] = None) -> Optional[str]:
        """Genera URL prefirmada para ver/descargar archivo (GET)"""
        pass
    
    @abstractmethod
    def check_file_exists(self, object_key: str) -> bool:
        """Verifica que el archivo existe en el storage"""
        pass
    
    @abstractmethod
    def delete_file(self, object_key: str) -> bool:
        """Elimina un archivo del storage"""
        pass


class S3Backend(StorageBackend):
    """Backend para AWS S3 (Producción)"""
    
    def __init__(self, config: dict):
        import boto3
        from botocore.config import Config
        
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=config['access_key'],
            aws_secret_access_key=config['secret_key'],
            region_name=config['region'],
            config=Config(signature_version='s3v4')
        )
        self.bucket = config['bucket_name']
        logger.info(f"AWS S3 Backend inicializado: {self.bucket}")
    
    def generate_upload_url(self, object_key: str, content_type: str, expiration: int = 300) -> Optional[str]:
        from botocore.exceptions import ClientError
        try:
            url = self.s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': object_key,
                    'ContentType': content_type
                },
                ExpiresIn=expiration
            )
            logger.debug(f"URL de subida generada para: {object_key}")
            return url
        except ClientError as e:
            logger.error(f"Error generando URL de subida S3: {e}")
            return None
    
    def generate_view_url(self, object_key: str, expiration: int = 3600, download_name: Optional[str] = None) -> Optional[str]:
        from botocore.exceptions import ClientError
        params = {'Bucket': self.bucket, 'Key': object_key}
        
        if download_name:
            params['ResponseContentDisposition'] = f'attachment; filename="{download_name}"'
        
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params=params,
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            logger.error(f"Error generando URL de visualización S3: {e}")
            return None
    
    def check_file_exists(self, object_key: str) -> bool:
        from botocore.exceptions import ClientError
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=object_key)
            return True
        except ClientError:
            return False
    
    def delete_file(self, object_key: str) -> bool:
        from botocore.exceptions import ClientError
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=object_key)
            logger.info(f"Archivo eliminado de S3: {object_key}")
            return True
        except ClientError as e:
            logger.error(f"Error eliminando archivo S3: {e}")
            return False


class MinIOBackend(StorageBackend):
    """Backend para MinIO (Desarrollo Local)"""
    
    def __init__(self, config: dict):
        import boto3
        from botocore.config import Config
        
        self.s3_client = boto3.client(
            's3',
            endpoint_url=config['endpoint_url'],
            aws_access_key_id=config['access_key'],
            aws_secret_access_key=config['secret_key'],
            region_name='us-east-1',  # MinIO no requiere región real
            config=Config(signature_version='s3v4')
        )
        self.bucket = config['bucket_name']
        self.endpoint_url = config['endpoint_url']
        
        # Auto-crear bucket si no existe
        self._ensure_bucket_exists()
        logger.info(f"MinIO Backend inicializado: {self.endpoint_url}/{self.bucket}")
    
    def _ensure_bucket_exists(self):
        """Crea el bucket automáticamente en desarrollo"""
        from botocore.exceptions import ClientError
        try:
            self.s3_client.head_bucket(Bucket=self.bucket)
            logger.debug(f"Bucket '{self.bucket}' ya existe")
        except ClientError:
            logger.warning(f"Creando bucket '{self.bucket}' en MinIO...")
            try:
                self.s3_client.create_bucket(Bucket=self.bucket)
                logger.info(f" Bucket '{self.bucket}' creado exitosamente")
            except ClientError as e:
                logger.error(f" Error creando bucket: {e}")
    
    def generate_upload_url(self, object_key: str, content_type: str, expiration: int = 300) -> Optional[str]:
        try:
            url = self.s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': object_key,
                    'ContentType': content_type
                },
                ExpiresIn=expiration
            )
            logger.debug(f"URL de subida MinIO generada para: {object_key}")
            return url
        except Exception as e:
            logger.error(f"Error generando URL de subida MinIO: {e}")
            return None
    
    def generate_view_url(self, object_key: str, expiration: int = 3600, download_name: Optional[str] = None) -> Optional[str]:
        params = {'Bucket': self.bucket, 'Key': object_key}
        
        if download_name:
            params['ResponseContentDisposition'] = f'attachment; filename="{download_name}"'
        
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params=params,
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            logger.error(f"Error generando URL de visualización MinIO: {e}")
            return None
    
    def check_file_exists(self, object_key: str) -> bool:
        try:
            self.s3_client.head_object(Bucket=self.bucket, Key=object_key)
            return True
        except Exception:
            return False
    
    def delete_file(self, object_key: str) -> bool:
        try:
            self.s3_client.delete_object(Bucket=self.bucket, Key=object_key)
            logger.info(f"Archivo eliminado de MinIO: {object_key}")
            return True
        except Exception as e:
            logger.error(f"Error eliminando archivo MinIO: {e}")
            return False
