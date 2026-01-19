# tests/clinical_files/test_file_lifecycle.py
"""
Tests end-to-end del ciclo de vida completo de archivos clínicos.
"""
import pytest
from django.urls import reverse
from rest_framework import status
import requests


@pytest.mark.django_db
@pytest.mark.slow
class TestCompleteFileLifecycle:
    """Tests del flujo completo: init → upload → confirm → view → delete"""
    
    def test_complete_file_upload_flow(self, authenticated_client, paciente_test, storage_service):
        """
        Test E2E del flujo completo de subida de archivo:
        1. Solicitar URL de subida (init-upload)
        2. Subir archivo a MinIO
        3. Confirmar subida (confirm-upload)
        4. Obtener URLs de visualización
        5. Eliminar archivo
        """
        # ========== PASO 1: Solicitar URL de subida ==========
        init_url = reverse('clinical_files:clinical-file-init-upload')
        init_data = {
            'paciente_id': str(paciente_test.id),
            'filename': 'radiografia_completa.jpg',
            'content_type': 'image/jpeg',
            'category': 'XRAY'
        }
        
        init_response = authenticated_client.post(init_url, init_data, format='json')
        
        assert init_response.status_code == status.HTTP_200_OK
        upload_url = init_response.data['upload_url']
        s3_key = init_response.data['s3_key']
        file_uuid = init_response.data['file_uuid']
        
        # ========== PASO 2: Subir archivo a MinIO ==========
        test_content = b"FAKE_XRAY_IMAGE_CONTENT_FOR_TESTING"
        upload_response = requests.put(
            upload_url,
            data=test_content,
            headers={'Content-Type': 'image/jpeg'}
        )
        
        assert upload_response.status_code == 200, f"MinIO upload failed: {upload_response.text}"
        
        # Verificar que el archivo existe en storage
        assert storage_service.check_file_exists(s3_key) is True
        
        # ========== PASO 3: Confirmar subida ==========
        confirm_url = reverse('clinical_files:clinical-file-confirm-upload')
        confirm_data = {
            's3_key': s3_key,
            'paciente_id': str(paciente_test.id),
            'filename': 'radiografia_completa.jpg',
            'content_type': 'image/jpeg',
            'size': len(test_content),
            'category': 'XRAY'
        }
        
        confirm_response = authenticated_client.post(confirm_url, confirm_data, format='json')
        
        assert confirm_response.status_code == status.HTTP_201_CREATED
        file_id = confirm_response.data['id']
        
        # ========== PASO 4: Obtener archivo por ID ==========
        detail_url = reverse('clinical_files:clinical-file-detail', kwargs={'pk': file_id})
        detail_response = authenticated_client.get(detail_url)
        
        assert detail_response.status_code == status.HTTP_200_OK
        assert detail_response.data['original_filename'] == 'radiografia_completa.jpg'
        assert detail_response.data['category'] == 'XRAY'
        
        # Verificar que se generaron URLs
        file_url = detail_response.data['file_url']
        download_url = detail_response.data['download_url']
        assert file_url is not None
        assert download_url is not None
        
        # ========== PASO 5: Descargar archivo usando URL prefirmada ==========
        download_response = requests.get(file_url)
        assert download_response.status_code == 200
        assert download_response.content == test_content
        
        # ========== PASO 6: Eliminar archivo ==========
        delete_response = authenticated_client.delete(detail_url)
        assert delete_response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verificar que se eliminó de storage
        assert storage_service.check_file_exists(s3_key) is False
        
        # Verificar que se eliminó de BD
        final_check = authenticated_client.get(detail_url)
        assert final_check.status_code == status.HTTP_404_NOT_FOUND
    
    def test_upload_multiple_files_same_patient(self, authenticated_client, paciente_test, storage_service):
        """Test de subida de múltiples archivos para el mismo paciente"""
        files_to_upload = [
            {'filename': 'radiografia1.jpg', 'category': 'XRAY'},
            {'filename': 'foto_intraoral.jpg', 'category': 'PHOTO'},
            {'filename': 'laboratorio.pdf', 'category': 'LAB'},
        ]
        
        uploaded_ids = []
        
        for file_data in files_to_upload:
            # Init upload
            init_url = reverse('clinical_files:clinical-file-init-upload')
            init_response = authenticated_client.post(init_url, {
                'paciente_id': str(paciente_test.id),
                'filename': file_data['filename'],
                'content_type': 'application/octet-stream',
                'category': file_data['category']
            }, format='json')
            
            assert init_response.status_code == status.HTTP_200_OK
            
            # Upload to MinIO
            upload_url = init_response.data['upload_url']
            s3_key = init_response.data['s3_key']
            requests.put(upload_url, data=b"TEST_CONTENT", headers={'Content-Type': 'application/octet-stream'})
            
            # Confirm
            confirm_url = reverse('clinical_files:clinical-file-confirm-upload')
            confirm_response = authenticated_client.post(confirm_url, {
                's3_key': s3_key,
                'paciente_id': str(paciente_test.id),
                'filename': file_data['filename'],
                'content_type': 'application/octet-stream',
                'size': 12,
                'category': file_data['category']
            }, format='json')
            
            assert confirm_response.status_code == status.HTTP_201_CREATED
            uploaded_ids.append((confirm_response.data['id'], s3_key))
        
        # Verificar que todos los archivos están listados
        list_url = reverse('clinical_files:clinical-file-by-patient', kwargs={'paciente_id': str(paciente_test.id)})
        list_response = authenticated_client.get(list_url)
        
        assert list_response.status_code == status.HTTP_200_OK
        assert list_response.data['total_archivos'] >= 3
        
        # Cleanup
        for file_id, s3_key in uploaded_ids:
            detail_url = reverse('clinical_files:clinical-file-detail', kwargs={'pk': file_id})
            authenticated_client.delete(detail_url)


@pytest.mark.django_db
@pytest.mark.security
class TestFileSecurityValidations:
    """Tests de seguridad y validaciones"""
    
    def test_cannot_confirm_without_actual_upload(self, authenticated_client, paciente_test):
        """Verifica que no se puede confirmar un archivo que no fue subido"""
        fake_key = f"pacientes/{paciente_test.id}/fake/nonexistent.jpg"
        
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
    
    def test_malicious_filename_rejected(self, authenticated_client, paciente_test):
        """Verifica que nombres de archivo maliciosos son rechazados"""
        url = reverse('clinical_files:clinical-file-init-upload')
        malicious_filenames = [
            '../../../etc/passwd',
            'C:\\Windows\\System32\\config',
            'file..exe',
            'test/../../secret.txt'
        ]
        
        for bad_filename in malicious_filenames:
            data = {
                'paciente_id': str(paciente_test.id),
                'filename': bad_filename,
                'content_type': 'text/plain'
            }
            
            response = authenticated_client.post(url, data, format='json')
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
