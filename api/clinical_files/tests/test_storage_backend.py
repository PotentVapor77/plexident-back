# api/clinical_files/tests/test_storage_backend.py
"""
Tests para verificar funcionalidad de MinIO/S3 backend.
"""
import time  
from datetime import datetime, date
import pytest
from common.services.storage_service import StorageService
from django.conf import settings
import requests
import uuid


@pytest.mark.django_db
class TestStorageBackend:
    """Tests del backend de almacenamiento (MinIO/S3)"""
    
    def test_storage_service_initialization(self, storage_service):
        """Verifica que el servicio se inicializa correctamente"""
        assert storage_service is not None
        assert storage_service._backend is not None
        assert storage_service._backend.bucket == settings.AWS_STORAGE_BUCKET_NAME
        print(f"✅ Storage inicializado: {storage_service._backend.bucket}")
    
    def test_generate_upload_url(self, storage_service):
        """Verifica generación de URL de subida"""
        test_key = f"test/upload_test_{uuid.uuid4()}.txt"
        content_type = "text/plain"
        
        url = storage_service.generate_upload_url(test_key, content_type)
        
        assert url is not None
        assert isinstance(url, str)
        assert len(url) > 0
        
        # Verificar que la URL contiene el bucket
        if settings.STORAGE_BACKEND == 'minio':
            assert 'localhost:9000' in url or '127.0.0.1:9000' in url
            print(f"✅ URL generada (MinIO): {url[:80]}...")
        else:
            assert 'amazonaws.com' in url
            print(f"✅ URL generada (S3): {url[:80]}...")
    
    def test_generate_view_url(self, storage_service):
        """Verifica generación de URL de visualización"""
        test_key = f"test/view_test_{uuid.uuid4()}.txt"
        
        url = storage_service.generate_view_url(test_key)
        
        assert url is not None
        assert isinstance(url, str)
        assert len(url) > 0
        print(f"✅ URL de visualización generada")
    
    def test_check_file_not_exists(self, storage_service):
        """Verifica que retorna False para archivos inexistentes"""
        fake_key = f"test/nonexistent_{uuid.uuid4()}.txt"
        
        exists = storage_service.check_file_exists(fake_key)
        
        assert exists is False
        print(f"✅ Correctamente detectó archivo inexistente")
    
    @pytest.mark.slow
    def test_upload_and_check_file_exists(self, storage_service):
        """Test completo: subir archivo y verificar existencia"""
        test_key = f"test/existence_test_{uuid.uuid4()}.txt"
        content_type = "text/plain"
        test_content = b"Test content for storage verification"
        
        # 1. Generar URL de subida
        upload_url = storage_service.generate_upload_url(test_key, content_type)
        assert upload_url is not None
        print(f"✅ URL de subida generada")
        
        # 2. Subir archivo usando la URL prefirmada
        response = requests.put(
            upload_url,
            data=test_content,
            headers={'Content-Type': content_type}
        )
        assert response.status_code == 200, f"Upload failed: {response.text}"
        print(f"✅ Archivo subido exitosamente a MinIO")
        
        # 3. Verificar que existe
        exists = storage_service.check_file_exists(test_key)
        assert exists is True
        print(f"✅ Archivo verificado en storage")
        
        # 4. Cleanup
        deleted = storage_service.delete_file(test_key)
        assert deleted is True
        print(f"✅ Archivo eliminado")
    
    @pytest.mark.slow
    def test_delete_file(self, storage_service):
        """Test de eliminación de archivos"""
        test_key = f"test/delete_test_{uuid.uuid4()}.txt"
        content_type = "text/plain"
        
        # Subir archivo primero
        upload_url = storage_service.generate_upload_url(test_key, content_type)
        requests.put(upload_url, data=b"To be deleted", headers={'Content-Type': content_type})
        
        # Verificar que existe
        assert storage_service.check_file_exists(test_key) is True
        print(f"✅ Archivo creado para test de eliminación")
        
        # Eliminar
        result = storage_service.delete_file(test_key)
        assert result is True
        print(f"✅ Archivo eliminado correctamente")
        
        # Verificar que ya no existe
        assert storage_service.check_file_exists(test_key) is False
        print(f"✅ Verificado que ya no existe")


@pytest.mark.django_db
class TestStorageURLs:
    """Tests específicos para URLs generadas"""
    
    def test_url_contains_signature(self, storage_service):
        """Verifica que las URLs contienen firma de seguridad"""
        s3_key = "test/secure_" + str(uuid.uuid4()) + ".txt"
        url = storage_service.generate_upload_url(s3_key, content_type="text/plain")
        
        # Verificar que contiene componentes de seguridad AWS
        assert "X-Amz-Algorithm" in url
        assert "X-Amz-Credential" in url
        assert "X-Amz-Signature" in url
        assert "X-Amz-Expires" in url
        
        print(f"✅ URL contiene firma de seguridad")
    
    def test_multiple_url_generations_are_unique(self, storage_service):
        """Verifica que múltiples generaciones de URL son únicas"""
        s3_key = "test/multi_" + str(uuid.uuid4()) + ".txt"
        urls = []
        
        for _ in range(3):
            url = storage_service.generate_upload_url(s3_key, content_type="text/plain")
            urls.append(url)
            time.sleep(1) 
        
        assert len(set(urls)) == 3, f"Expected 3 unique URLs, got {len(set(urls))}"
        print(f"✅ 3 URLs únicas generadas")
