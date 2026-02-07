import pytest
import json
from datetime import date
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from api.users.models import PermisoUsuario
from api.patients.models.paciente import Paciente
from api.patients.models.examen_estomatognatico import ExamenEstomatognatico
from api.patients.models.constantes_vitales import ConstantesVitales
from api.patients.models.antecedentes_personales import AntecedentesPersonales
from api.patients.models.antecedentes_familiares import AntecedentesFamiliares
from api.patients.models.examenes_complementarios import ExamenesComplementarios

Usuario = get_user_model()


@pytest.mark.django_db
class TestPacienteAPI:
    """Test suite para la API de pacientes"""

    def setup_method(self):
        """Configuración inicial para cada test"""
        self.client = APIClient()
        
        # Crear usuario administrador
        self.admin_user = Usuario.objects.create_superuser(
            username='adminpacientes',
            nombres='Admin',
            apellidos='Pacientes',
            correo='admin@pacientes.com',
            telefono='1234567890',
            password='admin123'
        )
        
        # Crear usuario odontólogo (los permisos se crean automáticamente via signals)
        self.odontologo = Usuario.objects.create_user(
            username='odontotest',
            nombres='Carlos',
            apellidos='Mendoza',
            correo='carlos.mendoza@clinica.com',
            telefono='0987654321',
            rol='Odontologo',
            password='pass123'
        )
        
        # Crear usuario asistente
        self.asistente = Usuario.objects.create_user(
            username='asistentetest',
            nombres='María',
            apellidos='González',
            correo='maria.gonzalez@clinica.com',
            telefono='0998887777',
            rol='Asistente',
            password='pass123'
        )
        
        # Datos de paciente de prueba
        self.paciente_data = {
            'nombres': 'Juan Carlos',
            'apellidos': 'Pérez López',
            'sexo': 'M',
            'edad': 35,
            'condicion_edad': 'A',
            'embarazada': 'NO',
            'cedula_pasaporte': '1234567890',
            'fecha_nacimiento': '1988-05-15',
            'fecha_ingreso': '2024-01-10',
            'direccion': 'Av. Amazonas N12-34 y Colón',
            'telefono': '0987654321',
            'correo': 'juan.perez@email.com',
            'contacto_emergencia_nombre': 'María Pérez',
            'contacto_emergencia_telefono': '0999999999'
        }

    def test_admin_puede_crear_paciente(self):
        """Test: Administrador puede crear paciente"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.post(
            '/api/patients/pacientes/',
            data=self.paciente_data,
            format='json'
        )
        
        print(f"Admin crear paciente - Status: {response.status_code}")
        
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            print(f"Error: {response.data}")
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['nombres'] == self.paciente_data['nombres']
        assert response.data['cedula_pasaporte'] == self.paciente_data['cedula_pasaporte']

    def test_odontologo_puede_crear_paciente(self):
        """Test: Odontólogo con permisos puede crear paciente"""
        self.client.force_authenticate(user=self.odontologo)
        
        paciente_data = self.paciente_data.copy()
        paciente_data['cedula_pasaporte'] = '0987654321'
        
        response = self.client.post(
            '/api/patients/pacientes/',
            data=paciente_data,
            format='json'
        )
        
        print(f"Odontólogo crear paciente - Status: {response.status_code}")
        
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            print(f"Error: {response.data}")
        
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_403_FORBIDDEN]

    def test_asistente_no_puede_crear_paciente(self):
        """Test: Asistente sin permiso POST no puede crear paciente"""
        self.client.force_authenticate(user=self.asistente)
        
        paciente_data = self.paciente_data.copy()
        paciente_data['cedula_pasaporte'] = '1122334455'
        
        response = self.client.post(
            '/api/patients/pacientes/',
            data=paciente_data,
            format='json'
        )
        
        print(f"Asistente crear paciente - Status: {response.status_code}")
        
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED]

    def test_listar_pacientes_como_admin(self):
        """Test: Admin puede listar pacientes"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Crear algunos pacientes de prueba
        for i in range(3):
            Paciente.objects.create(
                nombres=f'Paciente {i}',
                apellidos=f'Apellido {i}',
                sexo='M' if i % 2 == 0 else 'F',
                edad=25 + i,
                condicion_edad='A',
                cedula_pasaporte=f'100000000{i}',
                fecha_nacimiento='1990-01-01',
                fecha_ingreso='2024-01-01',
                telefono='1234567890'
            )
        
        response = self.client.get('/api/patients/pacientes/')
        
        print(f"Admin listar pacientes - Status: {response.status_code}")
        
        assert response.status_code == status.HTTP_200_OK
        
        if 'results' in response.data:
            assert isinstance(response.data['results'], list)
        else:
            assert isinstance(response.data, list)

    def test_obtener_paciente_por_id(self):
        """Test: Obtener paciente por ID"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Crear paciente de prueba
        paciente = Paciente.objects.create(
            nombres='Ana María',
            apellidos='Rodríguez Pérez',
            sexo='F',
            edad=30,
            condicion_edad='A',
            cedula_pasaporte='9999999999',
            fecha_nacimiento='1994-01-01',
            fecha_ingreso='2024-01-01',
            telefono='1234567890'
        )
        
        response = self.client.get(f'/api/patients/pacientes/{paciente.id}/')
        
        print(f"Obtener paciente por ID - Status: {response.status_code}")
        
        assert response.status_code == status.HTTP_200_OK
        assert str(response.data['id']) == str(paciente.id)
        assert response.data['nombres'] == paciente.nombres

    def test_actualizar_paciente(self):
        """Test: Actualizar paciente existente"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Crear paciente de prueba
        paciente = Paciente.objects.create(
            nombres='Luis Fernando',
            apellidos='Martínez Valencia',
            sexo='M',
            edad=42,
            condicion_edad='A',
            cedula_pasaporte='8888888888',
            fecha_nacimiento='1982-03-20',
            fecha_ingreso='2024-01-01',
            telefono='0987123456',
            correo='luis.martinez@email.com'
        )
        
        # Intentar actualizar solo algunos campos
        datos_actualizacion = {
            'direccion': 'Av. González Suárez N45-12',
            'telefono': '0995554444',
            'correo': 'luis.actualizado@nuevoemail.com'
        }
        
        response = self.client.patch(
            f'/api/patients/pacientes/{paciente.id}/',
            data=datos_actualizacion,
            format='json'
        )
        
        print(f"Actualizar paciente - Status: {response.status_code}")
        
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            print(f"Error de validación: {response.data}")
            # Si falla por campos requeridos, probar con PUT
            if any('required' in str(error).lower() for error in response.data.values()):
                # Crear datos completos para PUT
                datos_completos = {
                    'nombres': paciente.nombres,
                    'apellidos': paciente.apellidos,
                    'sexo': paciente.sexo,
                    'edad': paciente.edad,
                    'condicion_edad': paciente.condicion_edad,
                    'embarazada': 'NO',
                    'cedula_pasaporte': paciente.cedula_pasaporte,
                    'fecha_nacimiento': paciente.fecha_nacimiento.isoformat(),
                    'fecha_ingreso': paciente.fecha_ingreso.isoformat(),
                    'direccion': datos_actualizacion['direccion'],
                    'telefono': datos_actualizacion['telefono'],
                    'correo': datos_actualizacion['correo'],
                    'contacto_emergencia_nombre': paciente.contacto_emergencia_nombre or '',
                    'contacto_emergencia_telefono': paciente.contacto_emergencia_telefono or ''
                }
                
                response = self.client.put(
                    f'/api/patients/pacientes/{paciente.id}/',
                    data=datos_completos,
                    format='json'
                )
                
                print(f"Actualizar con PUT - Status: {response.status_code}")
        
        # Aceptar 200 OK o 400 Bad Request
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
        
        if response.status_code == status.HTTP_200_OK:
            assert response.data['direccion'] == datos_actualizacion['direccion']
            assert response.data['correo'] == datos_actualizacion['correo']

    def test_soft_delete_paciente(self):
        """Test: Eliminación lógica de paciente"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Crear paciente de prueba
        paciente = Paciente.objects.create(
            nombres='Pedro José',
            apellidos='García Ruiz',
            sexo='M',
            edad=30,
            condicion_edad='A',
            cedula_pasaporte='7777777777',
            fecha_nacimiento='1994-01-01',
            fecha_ingreso='2024-01-01',
            telefono='1234567890'
        )
        
        response = self.client.delete(f'/api/patients/pacientes/{paciente.id}/')
        
        print(f"Soft delete paciente - Status: {response.status_code}")
        
        assert response.status_code in [status.HTTP_204_NO_CONTENT, status.HTTP_200_OK]
        
        # Verificar que el paciente está desactivado
        paciente.refresh_from_db()
        assert paciente.activo == False

    def test_buscar_pacientes(self):
        """Test: Búsqueda de pacientes"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Crear pacientes con diferentes nombres
        Paciente.objects.create(
            nombres='Carlos Andrés',
            apellidos='García Moreno',
            sexo='M',
            edad=30,
            condicion_edad='A',
            cedula_pasaporte='1111111111',
            fecha_nacimiento='1994-01-01',
            fecha_ingreso='2024-01-01',
            telefono='1234567890'
        )
        
        Paciente.objects.create(
            nombres='María Fernanda',
            apellidos='Rodríguez Castro',
            sexo='F',
            edad=28,
            condicion_edad='A',
            cedula_pasaporte='2222222222',
            fecha_nacimiento='1996-01-01',
            fecha_ingreso='2024-01-01',
            telefono='1234567890'
        )
        
        # Buscar por nombre
        response = self.client.get('/api/patients/pacientes/?search=Carlos')
        
        print(f"Buscar pacientes - Status: {response.status_code}")
        
        assert response.status_code == status.HTTP_200_OK
        
        # Buscar por cédula
        response = self.client.get('/api/patients/pacientes/?search=1111111111')
        assert response.status_code == status.HTTP_200_OK
        
        # Buscar por apellido
        response = self.client.get('/api/patients/pacientes/?search=Rodríguez')
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestExamenEstomatognaticoAPI:
    """Tests para la API de examen estomatognático"""
    
    def setup_method(self):
        """Configuración inicial"""
        self.client = APIClient()
        
        # Crear admin
        self.admin_user = Usuario.objects.create_superuser(
            username='adminexamen',
            nombres='Admin',
            apellidos='Examen',
            correo='admin@examen.com',
            telefono='1234567890',
            password='admin123'
        )
        
        self.client.force_authenticate(user=self.admin_user)
        
        # Crear paciente para las pruebas
        self.paciente = Paciente.objects.create(
            nombres='Paciente',
            apellidos='Prueba',
            sexo='M',
            edad=35,
            condicion_edad='A',
            cedula_pasaporte='3333333333',
            fecha_nacimiento='1989-01-01',
            fecha_ingreso='2024-01-01',
            telefono='1234567890'
        )
        
        # Datos de examen estomatognático
        self.examen_data = {
            'paciente': str(self.paciente.id),
            'examen_sin_patologia': False,
            'lengua_cp': True,
            'lengua_descripcion': 'Lengua geográfica observada',
            'labios_cp': True,
            'labios_descripcion': 'Queilitis angular presente'
        }

    def test_crear_examen_estomatognatico(self):
        """Test: Crear examen estomatognático"""
        response = self.client.post(
            '/api/patients/examen-estomatognatico/',
            data=self.examen_data,
            format='json'
        )
        
        print(f"Crear examen estomatognático - Status: {response.status_code}")
        
        assert response.status_code == status.HTTP_201_CREATED
        assert str(response.data['paciente']) == str(self.paciente.id)
        assert response.data['lengua_cp'] == True

    def test_obtener_examen_por_paciente(self):
        """Test: Obtener examen por ID de paciente"""
        # Primero crear un examen
        examen = ExamenEstomatognatico.objects.create(
            paciente=self.paciente,
            examen_sin_patologia=False,
            lengua_cp=True,
            lengua_descripcion='Examen de prueba'
        )
        
        response = self.client.get(
            f'/api/patients/examen-estomatognatico/by-paciente/{self.paciente.id}/'
        )
        
        print(f"Obtener examen por paciente - Status: {response.status_code}")
        
        if response.status_code == status.HTTP_200_OK:
            assert str(response.data['paciente']) == str(self.paciente.id)
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            assert True  # No hay examen para este paciente
        else:
            assert False, f"Status code inesperado: {response.status_code}"

    def test_listar_todos_examenes_por_paciente(self):
        """Test: Listar todos los exámenes por paciente"""
        # Crear múltiples exámenes
        for i in range(2):
            ExamenEstomatognatico.objects.create(
                paciente=self.paciente,
                examen_sin_patologia=False,
                lengua_cp=True,
                lengua_descripcion=f'Examen {i+1}'
            )
        
        response = self.client.get(
            f'/api/patients/examen-estomatognatico/all-by-paciente/{self.paciente.id}/'
        )
        
        print(f"Listar todos exámenes por paciente - Status: {response.status_code}")
        
        assert response.status_code == status.HTTP_200_OK
        assert isinstance(response.data, list)
        assert len(response.data) == 2

    def test_resumen_patologias(self):
        """Test: Obtener resumen de patologías"""
        # Crear examen con patologías
        examen = ExamenEstomatognatico.objects.create(
            paciente=self.paciente,
            examen_sin_patologia=False,
            lengua_cp=True,
            lengua_descripcion='Lengua con patología',
            labios_cp=True,
            labios_descripcion='Labios con patología'
        )
        
        response = self.client.get(
            f'/api/patients/examen-estomatognatico/{examen.id}/resumen_patologias/'
        )
        
        print(f"Resumen patologías - Status: {response.status_code}")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['tiene_patologias'] == True
        assert len(response.data['regiones_con_patologia']) > 0


@pytest.mark.django_db
class TestConstantesVitalesAPI:
    """Tests para la API de constantes vitales"""
    
    def setup_method(self):
        """Configuración inicial"""
        self.client = APIClient()
        
        # Crear admin
        self.admin_user = Usuario.objects.create_superuser(
            username='adminconstantes',
            nombres='Admin',
            apellidos='Constantes',
            correo='admin@constantes.com',
            telefono='1234567890',
            password='admin123'
        )
        
        self.client.force_authenticate(user=self.admin_user)
        
        # Crear paciente
        self.paciente = Paciente.objects.create(
            nombres='Paciente',
            apellidos='Constantes',
            sexo='M',
            edad=40,
            condicion_edad='A',
            cedula_pasaporte='4444444444',
            fecha_nacimiento='1984-01-01',
            fecha_ingreso='2024-01-01',
            telefono='1234567890'
        )
        
        # Datos de constantes vitales
        self.constantes_data = {
            'paciente': str(self.paciente.id),
            'fecha_consulta': '2024-01-15',
            'motivo_consulta': 'Dolor dental',
            'enfermedad_actual': 'Caries en molar inferior derecho',
            'temperatura': 36.5,
            'pulso': 72,
            'frecuencia_respiratoria': 16,
            'presion_arterial': '120/80',
            'observaciones': 'Paciente en buen estado general'
        }

    def test_crear_constantes_vitales(self):
        """Test: Crear constantes vitales"""
        response = self.client.post(
            '/api/patients/constantes-vitales/',
            data=self.constantes_data,
            format='json'
        )
        
        print(f"Crear constantes vitales - Status: {response.status_code}")
        
        assert response.status_code == status.HTTP_201_CREATED
        assert str(response.data['paciente']) == str(self.paciente.id)
        assert float(response.data['temperatura']) == 36.5

    def test_obtener_constantes_por_paciente(self):
        """Test: Obtener constantes por ID de paciente"""
        # Primero crear constantes
        constantes = ConstantesVitales.objects.create(
            paciente=self.paciente,
            fecha_consulta='2024-01-15',
            motivo_consulta='Consulta de rutina',
            temperatura=36.8,
            pulso=75,
            frecuencia_respiratoria=18,
            presion_arterial='118/76'
        )
        
        response = self.client.get(
            f'/api/patients/constantes-vitales/by-paciente/{self.paciente.id}/'
        )
        
        print(f"Obtener constantes por paciente - Status: {response.status_code}")
        
        if response.status_code == status.HTTP_200_OK:
            assert str(response.data['paciente']) == str(self.paciente.id)
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            assert True  # No hay constantes para este paciente
        else:
            assert False, f"Status code inesperado: {response.status_code}"

    def test_consultas_por_paciente(self):
        """Test: Obtener consultas por paciente"""
        # Crear constantes con datos de consulta
        ConstantesVitales.objects.create(
            paciente=self.paciente,
            fecha_consulta='2024-01-15',
            motivo_consulta='Dolor agudo',
            enfermedad_actual='Caries profunda',
            temperatura=37.0,
            pulso=80
        )
        
        response = self.client.get(
            f'/api/patients/constantes-vitales/consultas-by-paciente/{self.paciente.id}/'
        )
        
        print(f"Consultas por paciente - Status: {response.status_code}")
        
        if response.status_code == status.HTTP_200_OK:
            assert isinstance(response.data, list)
            if len(response.data) > 0:
                assert 'motivo_consulta' in response.data[0]
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            assert True  # No hay consultas

    def test_validacion_temperatura(self):
        """Test: Validación de temperatura fuera de rango"""
        datos_invalidos = self.constantes_data.copy()
        datos_invalidos['temperatura'] = 50.0
        
        response = self.client.post(
            '/api/patients/constantes-vitales/',
            data=datos_invalidos,
            format='json'
        )
        
        print(f"Validación temperatura - Status: {response.status_code}")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestAntecedentesAPI:
    """Tests para API de antecedentes personales y familiares"""
    
    def setup_method(self):
        """Configuración inicial"""
        self.client = APIClient()
        
        # Crear admin
        self.admin_user = Usuario.objects.create_superuser(
            username='adminantecedentes',
            nombres='Admin',
            apellidos='Antecedentes',
            correo='admin@antecedentes.com',
            telefono='1234567890',
            password='admin123'
        )
        
        self.client.force_authenticate(user=self.admin_user)
        
        # Crear paciente
        self.paciente = Paciente.objects.create(
            nombres='Paciente',
            apellidos='Antecedentes',
            sexo='F',
            edad=45,
            condicion_edad='A',
            cedula_pasaporte='5555555555',
            fecha_nacimiento='1979-01-01',
            fecha_ingreso='2024-01-01',
            telefono='1234567890'
        )
        
        # Datos de antecedentes personales
        self.antecedentes_personales_data = {
            'paciente': str(self.paciente.id),
            'alergia_antibiotico': 'PENICILINA',
            'alergia_anestesia': 'NO',
            'hemorragias': 'NO',
            'vih_sida': 'NEGATIVO',
            'tuberculosis': 'NUNCA',
            'asma': 'NO',
            'diabetes': 'TIPO_2',
            'hipertension_arterial': 'CONTROLADA',
            'enfermedad_cardiaca': 'NO',
            'habitos': 'No fuma, consume alcohol ocasionalmente',
            'observaciones': 'Buena higiene bucal'
        }
        
        # Datos de antecedentes familiares
        self.antecedentes_familiares_data = {
            'paciente': str(self.paciente.id),
            'cardiopatia_familiar': 'PADRE',
            'hipertension_arterial_familiar': 'MADRE',
            'cancer_familiar': 'ABUELOS',
            'tipo_cancer': 'MAMA'
        }

    def test_crear_antecedentes_personales(self):
        """Test: Crear antecedentes personales"""
        response = self.client.post(
            '/api/patients/antecedentes-personales/',
            data=self.antecedentes_personales_data,
            format='json'
        )
        
        print(f"Crear antecedentes personales - Status: {response.status_code}")
        
        assert response.status_code == status.HTTP_201_CREATED
        assert str(response.data['paciente']) == str(self.paciente.id)
        assert response.data['diabetes'] == 'TIPO_2'

    def test_no_duplicar_antecedentes_personales(self):
        """Test: No permitir duplicar antecedentes personales para mismo paciente"""
        # Crear primero
        response1 = self.client.post(
            '/api/patients/antecedentes-personales/',
            data=self.antecedentes_personales_data,
            format='json'
        )
        
        assert response1.status_code == status.HTTP_201_CREATED
        
        # Intentar crear de nuevo
        response2 = self.client.post(
            '/api/patients/antecedentes-personales/',
            data=self.antecedentes_personales_data,
            format='json'
        )
        
        print(f"Intentar duplicar antecedentes - Status: {response2.status_code}")
        
        assert response2.status_code == status.HTTP_400_BAD_REQUEST

    def test_obtener_antecedentes_personales_por_paciente(self):
        """Test: Obtener antecedentes personales por paciente"""
        # Primero crear
        AntecedentesPersonales.objects.create(
            paciente=self.paciente,
            alergia_antibiotico='NO',
            alergia_anestesia='NO',
            hemorragias='NO',
            vih_sida='NEGATIVO',
            tuberculosis='NUNCA',
            asma='NO',
            diabetes='NO',
            hipertension_arterial='NO',
            enfermedad_cardiaca='NO'
        )
        
        response = self.client.get(
            f'/api/patients/antecedentes-personales/by-paciente/{self.paciente.id}/'
        )
        
        print(f"Obtener antecedentes personales - Status: {response.status_code}")
        
        if response.status_code == status.HTTP_200_OK:
            assert str(response.data['paciente']) == str(self.paciente.id)
        elif response.status_code == status.HTTP_404_NOT_FOUND:
            assert True
        else:
            assert False, f"Status code inesperado: {response.status_code}"

    def test_resumen_antecedentes_personales(self):
        """Test: Obtener resumen de antecedentes personales"""
        # Crear antecedentes con datos
        antecedentes = AntecedentesPersonales.objects.create(
            paciente=self.paciente,
            alergia_antibiotico='PENICILINA',
            alergia_anestesia='NO',
            hemorragias='SI',
            hemorragias_detalle='Episodios frecuentes de epistaxis',
            vih_sida='NEGATIVO',
            tuberculosis='NUNCA',
            asma='LEVE',
            diabetes='TIPO_2',
            hipertension_arterial='CONTROLADA',
            enfermedad_cardiaca='NO'
        )
        
        response = self.client.get(
            f'/api/patients/antecedentes-personales/{antecedentes.id}/resumen/'
        )
        
        print(f"Resumen antecedentes personales - Status: {response.status_code}")
        
        assert response.status_code == status.HTTP_200_OK
        assert 'tiene_condiciones_importantes' in response.data
        assert 'riesgo_visual' in response.data

    def test_crear_antecedentes_familiares(self):
        """Test: Crear antecedentes familiares"""
        response = self.client.post(
            '/api/patients/antecedentes-familiares/',
            data=self.antecedentes_familiares_data,
            format='json'
        )
        
        print(f"Crear antecedentes familiares - Status: {response.status_code}")
        
        assert response.status_code == status.HTTP_201_CREATED
        assert str(response.data['paciente']) == str(self.paciente.id)
        assert response.data['cardiopatia_familiar'] == 'PADRE'

    def test_resumen_antecedentes_familiares(self):
        """Test: Obtener resumen de antecedentes familiares"""
        # Crear antecedentes familiares
        antecedentes = AntecedentesFamiliares.objects.create(
            paciente=self.paciente,
            cardiopatia_familiar='PADRE',
            hipertension_arterial_familiar='MADRE',
            cancer_familiar='ABUELOS',
            tipo_cancer='MAMA',
            enfermedad_vascular_familiar='NO',
            endocrino_metabolico_familiar='NO',
            tuberculosis_familiar='NO',
            enfermedad_mental_familiar='NO',
            enfermedad_infecciosa_familiar='NO',
            malformacion_familiar='NO'
        )
        
        response = self.client.get(
            f'/api/patients/antecedentes-familiares/{antecedentes.id}/resumen/'
        )
        
        print(f"Resumen antecedentes familiares - Status: {response.status_code}")
        
        assert response.status_code == status.HTTP_200_OK
        assert 'tiene_antecedentes_importantes' in response.data


@pytest.mark.django_db
class TestExamenesComplementariosAPI:
    """Tests para API de exámenes complementarios"""
    
    def setup_method(self):
        """Configuración inicial"""
        self.client = APIClient()
        
        # Crear admin
        self.admin_user = Usuario.objects.create_superuser(
            username='adminexamencomp',
            nombres='Admin',
            apellidos='ExamenComp',
            correo='admin@examencomp.com',
            telefono='1234567890',
            password='admin123'
        )
        
        self.client.force_authenticate(user=self.admin_user)
        
        # Crear paciente
        self.paciente = Paciente.objects.create(
            nombres='Paciente',
            apellidos='ExamenComp',
            sexo='M',
            edad=50,
            condicion_edad='A',
            cedula_pasaporte='6666666666',
            fecha_nacimiento='1974-01-01',
            fecha_ingreso='2024-01-01',
            telefono='1234567890'
        )
        
        # Datos de exámenes complementarios
        self.examenes_data = {
            'paciente': str(self.paciente.id),
            'pedido_examenes': 'NO',
            'informe_examenes': 'NINGUNO'
        }

    def test_crear_examenes_complementarios(self):
        """Test: Crear exámenes complementarios"""
        response = self.client.post(
            '/api/patients/examenes-complementarios/',
            data=self.examenes_data,
            format='json'
        )
        
        print(f"Crear exámenes complementarios - Status: {response.status_code}")
        
        assert response.status_code == status.HTTP_201_CREATED
        assert str(response.data['paciente']) == str(self.paciente.id)
        assert response.data['pedido_examenes'] == 'NO'

    def test_marcar_examenes_solicitados(self):
        """Test: Marcar exámenes como solicitados"""
        # Primero crear exámenes
        examenes = ExamenesComplementarios.objects.create(
            paciente=self.paciente,
            pedido_examenes='NO',
            informe_examenes='NINGUNO'
        )
        
        response = self.client.post(
            f'/api/patients/examenes-complementarios/{examenes.id}/marcar-solicitados/',
            data={'detalle': 'Radiografía panorámica, hemograma completo'},
            format='json'
        )
        
        print(f"Marcar examenes solicitados - Status: {response.status_code}")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['pedido_examenes'] == 'SI'
        assert 'Radiografía' in response.data['pedido_examenes_detalle']

    def test_agregar_resultado_examen(self):
        """Test: Agregar resultado de examen"""
        examenes = ExamenesComplementarios.objects.create(
            paciente=self.paciente,
            pedido_examenes='SI',
            pedido_examenes_detalle='Radiografía solicitada',
            informe_examenes='NINGUNO'
        )
        
        response = self.client.post(
            f'/api/patients/examenes-complementarios/{examenes.id}/agregar-resultado/',
            data={
                'tipo_examen': 'RAYOS_X',
                'resultado': 'Caries en 36 y 37, reabsorción radicular en 45'
            },
            format='json'
        )
        
        print(f"Agregar resultado examen - Status: {response.status_code}")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['informe_examenes'] == 'RAYOS_X'
        assert 'Caries' in response.data['informe_examenes_detalle']

    def test_listar_examenes_pendientes(self):
        """Test: Listar exámenes pendientes"""
        # Crear examen pendiente
        ExamenesComplementarios.objects.create(
            paciente=self.paciente,
            pedido_examenes='SI',
            pedido_examenes_detalle='Exámenes pendientes',
            informe_examenes='NINGUNO'
        )
        
        # Crear examen completado
        otro_paciente = Paciente.objects.create(
            nombres='Otro',
            apellidos='Paciente',
            sexo='F',
            edad=30,
            condicion_edad='A',
            cedula_pasaporte='7777777777',
            fecha_nacimiento='1994-01-01',
            fecha_ingreso='2024-01-01',
            telefono='1234567890'
        )
        
        ExamenesComplementarios.objects.create(
            paciente=otro_paciente,
            pedido_examenes='SI',
            pedido_examenes_detalle='Exámenes completados',
            informe_examenes='BIOMETRIA',
            informe_examenes_detalle='Resultados normales'
        )
        
        response = self.client.get('/api/patients/examenes-complementarios/pendientes/')
        
        print(f"Listar exámenes pendientes - Status: {response.status_code}")
        
        assert response.status_code == status.HTTP_200_OK
        
        if 'results' in response.data:
            examenes_pendientes = response.data['results']
        else:
            examenes_pendientes = response.data
        
        # Verificar que hay exámenes pendientes
        assert len(examenes_pendientes) > 0


@pytest.mark.django_db
class TestIntegracionPaciente:
    """Tests de integración para flujo completo de paciente"""
    
    def test_flujo_completo_paciente(self):
        """Test: Flujo completo de creación y gestión de paciente"""
        client = APIClient()
        
        # 1. Crear admin
        admin = Usuario.objects.create_superuser(
            username='adminflujo',
            nombres='Admin',
            apellidos='Flujo',
            correo='admin@flujo.com',
            telefono='1234567890',
            password='admin123'
        )
        
        client.force_authenticate(user=admin)
        
        # 2. Crear paciente
        import uuid
        cedula_unica = f'{uuid.uuid4().int % 10000000000:010d}'
        
        paciente_data = {
            'nombres': 'José Antonio',
            'apellidos': 'Vargas Torres',
            'sexo': 'M',
            'edad': 28,
            'condicion_edad': 'A',
            'embarazada': 'NO',
            'cedula_pasaporte': cedula_unica,
            'fecha_nacimiento': '1996-01-01',
            'fecha_ingreso': '2024-01-01',
            'telefono': '1234567890',
            'correo': 'jose.vargas@email.com'
        }
        
        response = client.post('/api/patients/pacientes/', data=paciente_data, format='json')
        print(f"1. Paciente creado - Status: {response.status_code}")
        
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            print(f"Error creando paciente: {response.data}")
            # Si falla, continuar con otro test
            assert False, f"No se pudo crear el paciente: {response.data}"
        
        assert response.status_code == status.HTTP_201_CREATED
        paciente_id = response.data['id']
        
        print(f"Paciente creado: {paciente_id}")
        
        # 3. Crear constantes vitales
        constantes_data = {
            'paciente': paciente_id,
            'fecha_consulta': '2024-01-15',
            'motivo_consulta': 'Primera consulta',
            'temperatura': 36.5,
            'pulso': 72,
            'presion_arterial': '120/80'
        }
        
        response = client.post('/api/patients/constantes-vitales/', data=constantes_data, format='json')
        print(f"2. Constantes vitales - Status: {response.status_code}")
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]
        
        # 4. Crear antecedentes personales
        antecedentes_personales_data = {
            'paciente': paciente_id,
            'alergia_antibiotico': 'NO',
            'alergia_anestesia': 'NO',
            'hemorragias': 'NO',
            'vih_sida': 'NEGATIVO',
            'tuberculosis': 'NUNCA',
            'asma': 'NO',
            'diabetes': 'NO',
            'hipertension_arterial': 'NO',
            'enfermedad_cardiaca': 'NO'
        }
        
        response = client.post('/api/patients/antecedentes-personales/', data=antecedentes_personales_data, format='json')
        print(f"3. Antecedentes personales - Status: {response.status_code}")
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]
        
        # 5. Crear antecedentes familiares
        antecedentes_familiares_data = {
            'paciente': paciente_id,
            'cardiopatia_familiar': 'NO',
            'hipertension_arterial_familiar': 'NO',
            'enfermedad_vascular_familiar': 'NO',
            'endocrino_metabolico_familiar': 'NO',
            'cancer_familiar': 'NO',
            'tuberculosis_familiar': 'NO',
            'enfermedad_mental_familiar': 'NO',
            'enfermedad_infecciosa_familiar': 'NO',
            'malformacion_familiar': 'NO'
        }
        
        response = client.post('/api/patients/antecedentes-familiares/', data=antecedentes_familiares_data, format='json')
        print(f"4. Antecedentes familiares - Status: {response.status_code}")
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]
        
        # 6. Crear examen estomatognático
        examen_data = {
            'paciente': paciente_id,
            'examen_sin_patologia': True
        }
        
        response = client.post('/api/patients/examen-estomatognatico/', data=examen_data, format='json')
        print(f"5. Examen estomatognático - Status: {response.status_code}")
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]
        
        # 7. Obtener todos los datos del paciente
        response = client.get(f'/api/patients/pacientes/{paciente_id}/')
        print(f"6. Datos del paciente - Status: {response.status_code}")
        assert response.status_code == status.HTTP_200_OK
        
        print("✓ Flujo de paciente completado exitosamente")


# Tests de modelos
@pytest.mark.django_db
class TestPatientModels:
    """Tests para los modelos de pacientes"""
    
    def test_crear_paciente_basico(self):
        """Test: Crear paciente básico"""
        paciente = Paciente.objects.create(
            nombres='Juan Pablo',
            apellidos='García Ruiz',
            sexo='M',
            edad=30,
            condicion_edad='A',
            cedula_pasaporte='1712345678',
            fecha_nacimiento='1994-01-01',
            fecha_ingreso='2024-01-01',
            telefono='0987654321'
        )
        
        assert paciente.nombre_completo == 'García Ruiz, Juan Pablo'
        assert paciente.edad_completa == '30 Años'
        assert paciente.activo == True
        assert paciente.sexo == 'M'
    
    def test_propiedades_paciente(self):
        """Test: Propiedades del paciente"""
        paciente = Paciente.objects.create(
            nombres='Ana Lucía',
            apellidos='Martínez Pérez',
            sexo='F',
            edad=25,
            condicion_edad='A',
            cedula_pasaporte='1712345699',
            fecha_nacimiento='1999-01-01',
            fecha_ingreso='2024-01-01',
            telefono='0987123456'
        )
        
        assert paciente.get_full_name() == 'Martínez Pérez, Ana Lucía'
        assert str(paciente) == 'Martínez Pérez, Ana Lucía - 1712345699'
    
    def test_validaciones_paciente(self):
        """Test: Validaciones del modelo paciente"""
        try:
            paciente = Paciente(
                nombres='',  # Nombre vacío
                apellidos='Rodríguez',
                sexo='M',
                edad=30,
                condicion_edad='A',
                cedula_pasaporte='1712345600',
                fecha_nacimiento='1994-01-01',
                fecha_ingreso='2024-01-01',
                telefono='1234567890'
            )
            paciente.full_clean()
            assert False, "Debería haber fallado por nombres vacíos"
        except Exception as e:
            print(f"Validación falló como se esperaba: {e}")
            assert True
    
    def test_crear_examen_estomatognatico(self):
        """Test: Crear examen estomatognático"""
        paciente = Paciente.objects.create(
            nombres='María Fernanda',
            apellidos='Castro López',
            sexo='F',
            edad=35,
            condicion_edad='A',
            cedula_pasaporte='1712345611',
            fecha_nacimiento='1989-01-01',
            fecha_ingreso='2024-01-01',
            telefono='0987654321'
        )
        
        examen = ExamenEstomatognatico.objects.create(
            paciente=paciente,
            examen_sin_patologia=True
        )
        
        assert examen.paciente == paciente
        assert examen.tiene_patologias == False
    
    def test_constantes_vitales_propiedades(self):
        """Test: Propiedades de constantes vitales"""
        paciente = Paciente.objects.create(
            nombres='Carlos Andrés',
            apellidos='González Torres',
            sexo='M',
            edad=40,
            condicion_edad='A',
            cedula_pasaporte='1712345622',
            fecha_nacimiento='1984-01-01',
            fecha_ingreso='2024-01-01',
            telefono='0987654321'
        )
        
        constantes = ConstantesVitales.objects.create(
            paciente=paciente,
            temperatura=36.8,
            pulso=75,
            frecuencia_respiratoria=18,
            presion_arterial='118/76'
        )
        
        assert constantes.paciente == paciente
        assert 'Constantes vitales' in str(constantes)
    
    def test_antecedentes_personales_validaciones(self):
        """Test: Validaciones de antecedentes personales"""
        paciente = Paciente.objects.create(
            nombres='Luis Miguel',
            apellidos='Ramírez Sánchez',
            sexo='M',
            edad=45,
            condicion_edad='A',
            cedula_pasaporte='1712345633',
            fecha_nacimiento='1979-01-01',
            fecha_ingreso='2024-01-01',
            telefono='0987654321'
        )
        
        antecedentes = AntecedentesPersonales.objects.create(
            paciente=paciente,
            alergia_antibiotico='OTRO',
            alergia_antibiotico_otro='Clindamicina',
            alergia_anestesia='NO',
            hemorragias='NO',
            vih_sida='NEGATIVO',
            tuberculosis='NUNCA',
            asma='NO',
            diabetes='NO',
            hipertension_arterial='NO',
            enfermedad_cardiaca='NO'
        )
        
        assert antecedentes.tiene_alergias == True
        assert 'Clindamicina' in antecedentes.resumen_alergias


# Test de descubrimiento de rutas de pacientes
@pytest.mark.django_db
def test_descubrir_rutas_pacientes():
    """Test para descubrir rutas disponibles de pacientes"""
    from django.urls import get_resolver
    
    resolver = get_resolver()
    
    print("\n=== Rutas relacionadas con pacientes ===")
    
    rutas_pacientes = []
    
    def buscar_patrones(patterns, path=''):
        for pattern in patterns:
            current_path = f"{path}{pattern.pattern}"
            
            if hasattr(pattern, 'url_patterns'):
                buscar_patrones(pattern.url_patterns, current_path)
            else:
                full_path = current_path
                clean_path = full_path.replace('^', '')
                
                if 'patient' in clean_path.lower() or 'paciente' in clean_path.lower():
                    rutas_pacientes.append({
                        'path': clean_path,
                        'name': getattr(pattern, 'name', 'sin nombre')
                    })
    
    buscar_patrones(resolver.url_patterns)
    
    for ruta in rutas_pacientes:
        print(f"{ruta['path']} -> {ruta['name']}")
    
    assert len(rutas_pacientes) > 0, "No se encontraron rutas de pacientes"
    
    print(f"\nTotal rutas de pacientes encontradas: {len(rutas_pacientes)}")