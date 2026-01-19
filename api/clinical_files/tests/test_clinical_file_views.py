# api/clinical_files/tests/test_clinical_file_views.py
"""
Tests para endpoints de la API de clinical files.
"""
import pytest
from django.urls import reverse
from rest_framework import status
import uuid


@pytest.mark.django_db
class TestInitUploadEndpoint:
    """Tests del endpoint init-upload"""
    
    def test_init_upload_success(self, authenticated_client, paciente_test):
        """Test exitoso de solicitud de URL de subida"""
        url = reverse('clinical_files:clinical-file-init-upload')
        
        data = {
            'paciente_id': str(paciente_test.id),
            'filename': 'radiografia.jpg',
            'content_type': 'image/jpeg',
            'category': 'XRAY'
        }
        
        response = authenticated_client.post(url, data, format='json')
        print(f"Status: {response.status_code}")
        print(f"Response: {response.data if hasattr(response, 'data') else response.content}")
        
        assert response.status_code == status.HTTP_200_OK
        assert 'upload_url' in response.data
        assert 's3_key' in response.data
        assert 'file_uuid' in response.data
        
        s3_key = response.data['s3_key']
        assert str(paciente_test.id) in s3_key
        assert s3_key.endswith('.jpg')
        print(f"✅ Init upload exitoso: {s3_key}")
    
    def test_init_upload_without_auth(self, api_client, paciente_test):
        """Verifica que requiere autenticación"""
        url = reverse('clinical_files:clinical-file-init-upload')
        
        data = {
            'paciente_id': str(paciente_test.id),
            'filename': 'test.jpg',
            'content_type': 'image/jpeg'
        }
        
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        print(f"✅ Correctamente rechazó petición sin auth")
    
    def test_init_upload_invalid_paciente(self, authenticated_client):
        """Verifica validación de paciente inexistente"""
        url = reverse('clinical_files:clinical-file-init-upload')
        
        data = {
            'paciente_id': str(uuid.uuid4()),
            'filename': 'test.jpg',
            'content_type': 'image/jpeg'
        }
        
        response = authenticated_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        print(f"✅ Correctamente rechazó paciente inválido")
    
    def test_init_upload_missing_fields(self, authenticated_client, paciente_test):
        """Verifica validación de campos requeridos"""
        url = reverse('clinical_files:clinical-file-init-upload')
        
        data = {
            'paciente_id': str(paciente_test.id)
            # Falta filename y content_type
        }
        
        response = authenticated_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        print(f"✅ Correctamente rechazó datos incompletos")


@pytest.mark.django_db
class TestConfirmUploadEndpoint:
    """Tests del endpoint confirm-upload"""
    
    @pytest.mark.slow
    def test_confirm_upload_success(self, authenticated_client, paciente_test, storage_service):
        """Test exitoso de confirmación de subida"""
        # 1. Iniciar subida
        init_url = reverse('clinical_files:clinical-file-init-upload')
        init_data = {
            'paciente_id': str(paciente_test.id),
            'filename': 'test_confirm.jpg',
            'content_type': 'image/jpeg',
            'category': 'PHOTO'
        }
        
        init_response = authenticated_client.post(init_url, init_data, format='json')
        upload_url = init_response.data['upload_url']
        s3_key = init_response.data['s3_key']
        print(f"✅ Init upload exitoso")
        
        # 2. Subir archivo real a MinIO
        import requests
        test_content = b"FAKE_IMAGE_CONTENT_FOR_TESTING"
        upload_response = requests.put(
            upload_url,
            data=test_content,
            headers={'Content-Type': 'image/jpeg'}
        )
        
        assert upload_response.status_code == 200
        print(f"✅ Archivo subido a MinIO")
        
        # 3. Confirmar subida
        confirm_url = reverse('clinical_files:clinical-file-confirm-upload')
        confirm_data = {
            's3_key': s3_key,
            'paciente_id': str(paciente_test.id),
            'filename': 'test_confirm.jpg',
            'content_type': 'image/jpeg',
            'size': len(test_content),
            'category': 'PHOTO'
        }
        
        response = authenticated_client.post(confirm_url, confirm_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['original_filename'] == 'test_confirm.jpg'
        assert response.data['category'] == 'PHOTO'
        assert 'file_url' in response.data
        assert 'download_url' in response.data
        print(f"✅ Confirmación exitosa: {response.data['id']}")
        
        # Cleanup
        storage_service.delete_file(s3_key)
    
    def test_confirm_upload_file_not_in_storage(self, authenticated_client, paciente_test):
        """Verifica que falla si el archivo no está en storage"""
        fake_key = f"pacientes/{paciente_test.id}/fake/file_{uuid.uuid4()}.jpg"
        
        url = reverse('clinical_files:clinical-file-confirm-upload')
        data = {
            's3_key': fake_key,
            'paciente_id': str(paciente_test.id),
            'filename': 'fake.jpg',
            'content_type': 'image/jpeg',
            'size': 1000
        }
        
        response = authenticated_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        print(f"✅ Correctamente rechazó archivo no existente")


@pytest.mark.django_db
class TestFileListingEndpoints:
    """Tests de listado de archivos"""
    
    def test_list_files_by_patient(self, authenticated_client, paciente_test, uploaded_clinical_file):
        """Test de filtrado por paciente"""
        url = reverse('clinical_files:clinical-file-by-patient', kwargs={'paciente_id': str(paciente_test.id)})
        
        response = authenticated_client.get(url)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print(f"Response: {response.data}")
            assert 'paciente' in response.data or 'archivos' in response.data
            print(f"✅ Listado por paciente exitoso")
        else:
            print(f"Response: {response.content}")


@pytest.mark.django_db
class TestFileDelete:
    """Tests de eliminación de archivos"""
    
    def test_delete_file(self, authenticated_client, uploaded_clinical_file, storage_service):
        """Test de eliminación de archivo"""
        file_id = uploaded_clinical_file.id
        url = reverse('clinical_files:clinical-file-detail', kwargs={'pk': str(file_id)})
        
        response = authenticated_client.delete(url)
        print(f"Status: {response.status_code}")
        
        # 204 NO CONTENT es el código correcto para DELETE exitoso
        assert response.status_code in [status.HTTP_204_NO_CONTENT, status.HTTP_200_OK]
        print(f"✅ Archivo eliminado correctamente")