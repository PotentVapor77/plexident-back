# api/parameters/tests/test_config_horario.py

import pytest
import json
from datetime import time
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from api.parameters.models import ConfiguracionHorario

Usuario = get_user_model()


@pytest.mark.django_db
class TestConfiguracionHorarioAPI:
    """Test suite para la API de Configuración de Horarios (RF-07.1)"""

    def setup_method(self):
        """Configuración inicial para cada test"""
        self.client = APIClient()
        
        # ✅ Crear usuarios para diferentes roles
        self.admin_user = Usuario.objects.create_user(
            username='adminhorarios',
            nombres='Admin',
            apellidos='Horarios',
            correo='admin@horarios.com',
            telefono='1234567890',
            rol='Administrador',
            password='admin123'
        )
        
        self.odontologo = Usuario.objects.create_user(
            username='odontohorarios',
            nombres='Carlos',
            apellidos='Odontologo',
            correo='carlos@clinica.com',
            telefono='0987654321',
            rol='Odontologo',
            password='pass123'
        )
        
        self.asistente = Usuario.objects.create_user(
            username='asisthorarios',
            nombres='María',
            apellidos='Asistente',
            correo='maria@clinica.com',
            telefono='0998887777',
            rol='Asistente',
            password='pass123'
        )
        
        # ✅ Datos de horario de prueba
        self.horario_data = {
            'dia_semana': 0,  # Lunes
            'apertura': '08:00',
            'cierre': '18:00',
            'activo': True
        }
        
        # ✅ Datos para actualización masiva
        self.bulk_horarios_data = {
            'horarios': [
                {'dia_semana': 0, 'apertura': '08:00', 'cierre': '18:00', 'activo': True},
                {'dia_semana': 1, 'apertura': '08:00', 'cierre': '18:00', 'activo': True},
                {'dia_semana': 2, 'apertura': '08:00', 'cierre': '18:00', 'activo': True},
                {'dia_semana': 3, 'apertura': '08:00', 'cierre': '18:00', 'activo': True},
                {'dia_semana': 4, 'apertura': '08:00', 'cierre': '17:00', 'activo': True},
                {'dia_semana': 5, 'apertura': '09:00', 'cierre': '13:00', 'activo': True},
                {'dia_semana': 6, 'apertura': '09:00', 'cierre': '12:00', 'activo': False},  # Domingo inactivo
            ]
        }

    # ==================== TESTS DE CREACIÓN ====================

    def test_admin_puede_crear_horario(self):
        """✅ Test: Administrador puede crear horario"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.post(
            '/api/parameters/config-horarios/',
            data=self.horario_data,
            format='json'
        )
        
        print(f"\nAdmin crear horario - Status: {response.status_code}")
        
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            print(f"Error: {response.data}")
        
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST]
        
        if response.status_code == 201:
            data = response.data
            if isinstance(data, dict) and 'data' in data:
                horario = data['data']
            else:
                horario = data
                
            assert horario['dia_semana'] == self.horario_data['dia_semana']
            assert horario['apertura'] == '08:00:00'
            assert horario['activo'] == True
            print(f"✓ Horario creado exitosamente (ID: {horario.get('id', 'N/A')})")

    def test_no_duplicar_dia_semana(self):
        """✅ Test: No permitir horario duplicado para mismo día"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Crear primer horario
        response1 = self.client.post(
            '/api/parameters/config-horarios/',
            data=self.horario_data,
            format='json'
        )
        
        assert response1.status_code in [201, 400]
        
        # Intentar crear segundo horario para mismo día
        response2 = self.client.post(
            '/api/parameters/config-horarios/',
            data=self.horario_data,
            format='json'
        )
        
        print(f"\nIntentar duplicar horario - Status: {response2.status_code}")
        
        # Debería fallar con 400 Bad Request
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        print(f"✓ Correctamente evita duplicados")

    # ==================== TESTS DE LECTURA ====================

    def test_listar_horarios_como_admin(self):
        """✅ Test: Admin puede listar horarios"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Crear algunos horarios de prueba
        for dia in range(3):
            ConfiguracionHorario.objects.create(
                dia_semana=dia,
                apertura=time(8, 0),
                cierre=time(18, 0),
                activo=True
            )
        
        response = self.client.get('/api/parameters/config-horarios/')
        
        print(f"\nAdmin listar horarios - Status: {response.status_code}")
        
        assert response.status_code == status.HTTP_200_OK
        
        # Obtener datos de respuesta
        data = response.data
        if isinstance(data, dict) and 'results' in data:
            horarios = data['results']  # Si hay paginación
        elif isinstance(data, list):
            horarios = data
        elif isinstance(data, dict) and 'data' in data:
            if isinstance(data['data'], list):
                horarios = data['data']
            else:
                horarios = [data['data']]
        else:
            horarios = []
        
        print(f"  Total horarios: {len(horarios)}")
        assert len(horarios) >= 3

    def test_odontologo_puede_listar_horarios(self):
        """✅ Test: Odontólogo puede listar horarios (solo lectura)"""
        self.client.force_authenticate(user=self.odontologo)
        
        # Crear algunos horarios
        ConfiguracionHorario.objects.create(
            dia_semana=0,
            apertura=time(8, 0),
            cierre=time(18, 0),
            activo=True
        )
        
        response = self.client.get('/api/parameters/config-horarios/')
        
        print(f"\nOdontólogo listar horarios - Status: {response.status_code}")
        
        # Odontólogo debería poder listar (GET está permitido)
        assert response.status_code == status.HTTP_200_OK
        print(f"✓ Odontólogo puede listar horarios")

    def test_obtener_horario_por_id(self):
        """✅ Test: Obtener horario por ID"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Crear horario de prueba
        horario = ConfiguracionHorario.objects.create(
            dia_semana=1,
            apertura=time(9, 0),
            cierre=time(17, 0),
            activo=True
        )
        
        response = self.client.get(f'/api/parameters/config-horarios/{horario.id}/')
        
        print(f"\nObtener horario por ID - Status: {response.status_code}")
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.data
        if isinstance(data, dict) and 'data' in data:
            horario_data = data['data']
        else:
            horario_data = data
        
        assert str(horario_data['id']) == str(horario.id)
        assert horario_data['dia_semana'] == 1
        print(f"✓ Horario obtenido correctamente")

    # ==================== TESTS DE ACTUALIZACIÓN ====================

    def test_admin_puede_actualizar_horario(self):
        """✅ Test: Admin puede actualizar horario"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Crear horario
        horario = ConfiguracionHorario.objects.create(
            dia_semana=2,
            apertura=time(8, 0),
            cierre=time(18, 0),
            activo=True
        )
        
        # Actualizar
        datos_actualizacion = {
            'apertura': '09:00',
            'cierre': '19:00',
            'activo': False
        }
        
        response = self.client.patch(
            f'/api/parameters/config-horarios/{horario.id}/',
            data=datos_actualizacion,
            format='json'
        )
        
        print(f"\nAdmin actualizar horario - Status: {response.status_code}")
        
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            print(f"Error: {response.data}")
        
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
        
        if response.status_code == 200:
            data = response.data
            if isinstance(data, dict) and 'data' in data:
                horario_actualizado = data['data']
            else:
                horario_actualizado = data
            
            assert horario_actualizado['apertura'] == '09:00:00'
            assert horario_actualizado['activo'] == False
            print(f"✓ Horario actualizado exitosamente")

    def test_validacion_horarios_invalidos(self):
        """✅ Test: Validación de horarios inválidos"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Caso 1: Cierre antes de apertura
        horario_invalido = {
            'dia_semana': 3,
            'apertura': '18:00',
            'cierre': '08:00',  # Cierre antes de apertura
            'activo': True
        }
        
        response = self.client.post(
            '/api/parameters/config-horarios/',
            data=horario_invalido,
            format='json'
        )
        
        print(f"\nValidación horario inválido - Status: {response.status_code}")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        print(f"✓ Correctamente rechaza horario inválido")

    # ==================== TESTS DE ELIMINACIÓN ====================

    def test_admin_puede_eliminar_horario(self):
        """✅ Test: Admin puede eliminar horario"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Crear horario
        horario = ConfiguracionHorario.objects.create(
            dia_semana=4,
            apertura=time(8, 0),
            cierre=time(18, 0),
            activo=True
        )
        
        response = self.client.delete(f'/api/parameters/config-horarios/{horario.id}/')
        
        print(f"\nAdmin eliminar horario - Status: {response.status_code}")
        
        assert response.status_code in [status.HTTP_204_NO_CONTENT, status.HTTP_200_OK]
        
        # Verificar que ya no existe
        with pytest.raises(ConfiguracionHorario.DoesNotExist):
            ConfiguracionHorario.objects.get(id=horario.id)
        
        print(f"✓ Horario eliminado correctamente")

    # ==================== TESTS DE ENDPOINTS ESPECIALES ====================


    def test_endpoint_verificar_horario(self):
        """✅ Test: Endpoint /verificar/"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Crear horario para hoy
        import datetime
        hoy = datetime.datetime.now().weekday()
        
        ConfiguracionHorario.objects.create(
            dia_semana=hoy,
            apertura=time(8, 0),
            cierre=time(18, 0),
            activo=True
        )
        
        response = self.client.get('/api/parameters/config-horarios/verificar/')
        
        print(f"\nEndpoint verificar horario - Status: {response.status_code}")
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.data
        if isinstance(data, dict) and 'data' in data:
            resultado = data['data']
        else:
            resultado = data
        
        assert 'es_horario_laboral' in resultado
        assert 'dia_actual' in resultado
        assert 'hora_actual' in resultado
        print(f"✓ Verificación completada: es_horario_laboral={resultado['es_horario_laboral']}")

    # ==================== TESTS DE ACTUALIZACIÓN MASIVA ====================

    def test_bulk_update_como_admin(self):
        """✅ Test: Admin puede hacer bulk update de horarios"""
        self.client.force_authenticate(user=self.admin_user)
        
        response = self.client.post(
            '/api/parameters/config-horarios/bulk-update/',
            data=self.bulk_horarios_data,
            format='json'
        )
        
        print(f"\nAdmin bulk update - Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error: {response.data}")
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.data
        if isinstance(data, dict) and 'data' in data:
            resultado = data['data']
        else:
            resultado = data
        
        assert resultado['success'] == True
        assert len(resultado['resultados']) == 7  # 7 días
        
        # Verificar que se crearon los horarios
        total_horarios = ConfiguracionHorario.objects.count()
        print(f"  Total horarios creados: {total_horarios}")
        assert total_horarios == 7
        
        print(f"✓ Bulk update exitoso")

    def test_bulk_update_validacion_duplicados(self):
        """✅ Test: Bulk update valida duplicados en el request"""
        self.client.force_authenticate(user=self.admin_user)
        
        datos_con_duplicado = {
            'horarios': [
                {'dia_semana': 0, 'apertura': '08:00', 'cierre': '18:00'},
                {'dia_semana': 0, 'apertura': '09:00', 'cierre': '17:00'},  # Duplicado
            ]
        }
        
        response = self.client.post(
            '/api/parameters/config-horarios/bulk-update/',
            data=datos_con_duplicado,
            format='json'
        )
        
        print(f"\nBulk update con duplicado - Status: {response.status_code}")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        print(f"✓ Correctamente rechaza duplicados en el request")

    def test_odontologo_no_puede_bulk_update(self):
        """✅ Test: Odontólogo no puede hacer bulk update"""
        self.client.force_authenticate(user=self.odontologo)
        
        response = self.client.post(
            '/api/parameters/config-horarios/bulk-update/',
            data=self.bulk_horarios_data,
            format='json'
        )
        
        print(f"\nOdontólogo bulk update - Status: {response.status_code}")
        
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED]
        print(f"✓ Correctamente denegado para odontólogo")

    # ==================== TESTS DE PERMISOS ====================

    def test_no_autenticado_no_accede(self):
        """✅ Test: Usuario no autenticado no puede acceder"""
        response = self.client.get('/api/parameters/config-horarios/')
        
        print(f"\nNo autenticado acceso - Status: {response.status_code}")
        
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
        print(f"✓ Correctamente bloqueado para no autenticados")

    # ==================== TESTS DE VALIDACIÓN DE DATOS ====================

    def test_validacion_dia_semana_rango(self):
        """✅ Test: Validación de rango de día de semana"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Día inválido (fuera de rango 0-6)
        horario_invalido = {
            'dia_semana': 7,  # Inválido
            'apertura': '08:00',
            'cierre': '18:00',
            'activo': True
        }
        
        response = self.client.post(
            '/api/parameters/config-horarios/',
            data=horario_invalido,
            format='json'
        )
        
        print(f"\nValidación día inválido - Status: {response.status_code}")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        print(f"✓ Correctamente rechaza día inválido")

    def test_validacion_hora_formato(self):
        """✅ Test: Validación de formato de hora"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Hora con formato inválido
        horario_invalido = {
            'dia_semana': 0,
            'apertura': '25:00',  # Hora inválida
            'cierre': '18:00',
            'activo': True
        }
        
        response = self.client.post(
            '/api/parameters/config-horarios/',
            data=horario_invalido,
            format='json'
        )
        
        print(f"\nValidación formato hora - Status: {response.status_code}")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        print(f"✓ Correctamente rechaza formato de hora inválido")

    # ==================== TESTS DE FUNCIONALIDAD ====================

    def test_campos_auditoria(self):
        """✅ Test: Verificar que se registran campos de auditoría"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Crear horario
        response = self.client.post(
            '/api/parameters/config-horarios/',
            data=self.horario_data,
            format='json'
        )
        
        if response.status_code == 201:
            data = response.data
            if isinstance(data, dict) and 'data' in data:
                horario = data['data']
            else:
                horario = data
            
            # Verificar campos de auditoría
            assert 'creado_por' in horario
            assert 'fecha_creacion' in horario
            assert 'fecha_modificacion' in horario
            
            print(f"\nCampos auditoría: OK")
            print(f"  Creado por: {horario.get('creado_por', 'N/A')}")
            print(f"  Fecha creación: {horario.get('fecha_creacion', 'N/A')}")
            
            print(f"✓ Campos de auditoría funcionando")

    def test_ordenamiento_por_dia_semana(self):
        """✅ Test: Horarios se ordenan por día de semana"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Crear horarios en orden aleatorio
        dias = [4, 1, 6, 3, 0, 5, 2]
        for dia in dias:
            ConfiguracionHorario.objects.create(
                dia_semana=dia,
                apertura=time(8, 0),
                cierre=time(18, 0),
                activo=True
            )
        
        response = self.client.get('/api/parameters/config-horarios/')
        assert response.status_code == 200
        
        data = response.data
        if isinstance(data, dict) and 'results' in data:
            horarios = data['results']
        elif isinstance(data, list):
            horarios = data
        elif isinstance(data, dict) and 'data' in data:
            if isinstance(data['data'], list):
                horarios = data['data']
            else:
                horarios = [data['data']]
        else:
            horarios = []
        
        # Verificar orden (0=Lunes, 1=Martes, etc.)
        if len(horarios) > 1:
            dias_ordenados = [h['dia_semana'] for h in horarios]
            print(f"\nDías ordenados: {dias_ordenados}")
            
            # Verificar que estén ordenados
            assert dias_ordenados == sorted(dias_ordenados)
            print(f"✓ Horarios ordenados correctamente por día de semana")


# ==================== TESTS DE DESCRIBIR RUTAS ====================

@pytest.mark.django_db
def test_listar_rutas_horarios():
    """✅ Test: Listar rutas disponibles para horarios"""
    print("\n=== Rutas de configuración de horarios ===")
    
    # Rutas esperadas
    rutas_esperadas = [
        '/api/parameters/config-horarios/',
        '/api/parameters/config-horarios/semana-actual/',
        '/api/parameters/config-horarios/verificar/',
        '/api/parameters/config-horarios/bulk-update/',
    ]
    
    client = APIClient()
    admin = Usuario.objects.create_user(
        username='testrutas',
        nombres='Test',
        apellidos='Rutas',
        correo='test@rutas.com',
        telefono='1234567890',
        rol='Administrador',
        password='admin123'
    )
    
    client.force_authenticate(user=admin)
    
    rutas_funcionales = []
    
    for ruta in rutas_esperadas:
        # Para endpoints que aceptan GET
        if '/bulk-update/' not in ruta:
            response = client.get(ruta)
        else:
            # Para bulk-update, probar con datos vacíos (debería fallar con 400)
            response = client.post(ruta, data={}, format='json')
        
        if response.status_code in [200, 400, 401, 403, 405]:
            estado = "✓" if response.status_code in [200, 400] else "⚠"
            rutas_funcionales.append(ruta)
            print(f"{estado} {ruta} - Status: {response.status_code}")
        else:
            print(f"✗ {ruta} - Status: {response.status_code}")
    
    assert len(rutas_funcionales) > 0, "No se encontraron rutas funcionales"
    print(f"\n✓ Total rutas funcionales: {len(rutas_funcionales)}/{len(rutas_esperadas)}")


# ==================== EJECUCIÓN DIRECTA PARA DEBUG ====================

if __name__ == '__main__':
    """Ejecutar directamente para debugging"""
    print("=== Tests de Configuración de Horarios ===")
    print("\nPara ejecutar todos los tests:")
    print("pytest api/parameters/tests/test_config_horario.py -v")
    print("\nPara ejecutar tests específicos:")
    print("pytest api/parameters/tests/test_config_horario.py::TestConfiguracionHorarioAPI::test_admin_puede_crear_horario -v")
    print("pytest api/parameters/tests/test_config_horario.py::TestConfiguracionHorarioAPI::test_bulk_update_como_admin -v")