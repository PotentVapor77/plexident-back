# api/clinical_files/tests/conftest.py
"""
Fixtures compartidas para tests de clinical files.
Adaptado a los modelos personalizados de Plexident.
"""
import pytest
from django.contrib.auth import get_user_model
from api.odontogram.models import Paciente, HistorialOdontograma
from api.clinical_files.models import ClinicalFile
from common.services.storage_service import StorageService
import uuid
from datetime import date, datetime

User = get_user_model()


@pytest.fixture
def odontologo_user(db):
    """Usuario odontólogo para tests"""
    user = User.objects.create_user(
        username='test_odontologo',
        correo='odontologo@test.com',
        password='testpass123',
        nombres='Juan',
        apellidos='Pérez',
        rol='Odontologo',  
        telefono='0999999999'  
    )
    return user


@pytest.fixture
def paciente_test(db):
    """Paciente de prueba"""
    paciente = Paciente.objects.create(
        nombres='María',
        apellidos='González',
        cedula_pasaporte='0999999999',
        fecha_nacimiento=date(1990, 5, 15),
        sexo='F',
        telefono='0999999999',
        correo='maria.gonzalez@test.com',  
        edad=35,  
        condicion_edad='A',  
        fecha_ingreso=datetime.now()  
    )
    return paciente


@pytest.fixture
def snapshot_test(db, paciente_test, odontologo_user):
    """Snapshot de historial de odontograma"""
    snapshot = HistorialOdontograma.objects.create(
        paciente=paciente_test,
        odontologo=odontologo_user,
        version_id=uuid.uuid4(),
        tipo_cambio='DIAGNOSTICO_AGREGADO',
        fecha=datetime.now()
    )
    return snapshot


@pytest.fixture
def storage_service():
    """Instancia del servicio de storage"""
    return StorageService()


@pytest.fixture
def sample_file_data():
    """Datos de ejemplo para un archivo"""
    return {
        'filename': 'radiografia_test.jpg',
        'content_type': 'image/jpeg',
        'content': b'FAKE_IMAGE_CONTENT_FOR_TESTING',
        'size': 31,
        'category': 'XRAY'
    }


@pytest.fixture
def uploaded_clinical_file(db, paciente_test, odontologo_user, storage_service):
    """Archivo clínico ya subido (para tests de lectura/eliminación)"""
    file_uuid = uuid.uuid4()
    s3_key = f"pacientes/{paciente_test.id}/snapshots/general/archivos/{file_uuid}.jpg"
    
    clinical_file = ClinicalFile.objects.create(
        paciente=paciente_test,
        bucket_name=storage_service._backend.bucket,
        s3_key=s3_key,
        original_filename='radiografia_test.jpg',
        mime_type='image/jpeg',
        file_size_bytes=1024,
        category='XRAY',
        uploaded_by=odontologo_user
    )
    
    yield clinical_file
    
    # Cleanup: eliminar del storage si existe
    try:
        storage_service.delete_file(s3_key)
    except:
        pass


@pytest.fixture
def api_client():
    """Cliente API"""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, odontologo_user):
    """Cliente API autenticado"""
    api_client.force_authenticate(user=odontologo_user)
    return api_client
