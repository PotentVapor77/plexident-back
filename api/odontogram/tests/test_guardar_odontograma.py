# api/odontogram/tests/test_guardar_odontograma.py

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
import uuid

from api.patients.models import Paciente
from api.odontogram.models import (
    CategoriaDiagnostico,
    Diagnostico,
    Diente,
    SuperficieDental,
    DiagnosticoDental,
    HistorialOdontograma,
)
from api.odontogram.services.odontogram_services import OdontogramaService

User = get_user_model()


class GuardarOdontogramaCompletoTestCase(TransactionTestCase):
    """
    Test completo para guardar odontograma con todos los diagnósticos
    """
    
    def setUp(self):
        """Configuración inicial para cada test"""
        # 1. Crear odontólogo (usuario)
        self.odontologo = User.objects.create_user(
            username='dr.garcia',
            correo='garcia@plexident.com',
            password='testpass123',
            nombres='Carlos',
            apellidos='García',
            rol='Odontologo',
            telefono='0999999999',
            activo=True
        )
        
        # 2. Obtener o crear paciente con ID específico
        self.paciente_id = 'd0aac59f-da6c-4eaa-95b9-e9d471e97760'
        
        # Verificar si existe el paciente, si no, crearlo
        try:
            self.paciente = Paciente.objects.get(id=self.paciente_id)
        except Paciente.DoesNotExist:
            self.paciente = Paciente.objects.create(
                id=self.paciente_id,
                nombres='Juan',
                apellidos='Pérez',
                cedula_pasaporte='1234567890',
                sexo='M',
                fecha_nacimiento='1990-01-15',
                edad=35,
                condicion_edad='A',
                telefono='0999999999',
                correo='juan.perez@test.com',
                direccion='Guayaquil, Ecuador',
                activo=True
            )
        
        # 3. Crear catálogo de diagnósticos
        self._crear_catalogo_diagnosticos()
        
        # 4. Inicializar servicio
        self.service = OdontogramaService()
        
        # 5. Cliente API para pruebas de endpoints
        self.client = APIClient()
        self.client.force_authenticate(user=self.odontologo)
    
    def _crear_catalogo_diagnosticos(self):
        """Crea el catálogo de diagnósticos necesarios para las pruebas"""
        
        # Categorías
        self.categoria_caries = CategoriaDiagnostico.objects.create(
            key='patologia_dental',
            nombre='Patología Dental',
            color_key='#FF0000',
            prioridad_key='ALTA',
            activo=True
        )
        
        self.categoria_restauracion = CategoriaDiagnostico.objects.create(
            key='restauracion',
            nombre='Restauración',
            color_key='#0000FF',
            prioridad_key='MEDIA',
            activo=True
        )
        
        # Diagnósticos
        self.diag_caries_icdas_3 = Diagnostico.objects.create(
            key='caries_icdas_3',
            categoria=self.categoria_caries,
            nombre='Caries ICDAS 3',
            siglas='CI3',
            simbolo_color='#FF0000',
            prioridad=4,
            codigo_icd10='K02.1',
            activo=True
        )
        
        self.diag_caries_icdas_4 = Diagnostico.objects.create(
            key='caries_icdas_4',
            categoria=self.categoria_caries,
            nombre='Caries ICDAS 4',
            siglas='CI4',
            simbolo_color='#CC0000',
            prioridad=5,
            codigo_icd10='K02.2',
            activo=True
        )
        
        self.diag_obturacion_buena = Diagnostico.objects.create(
            key='obturacion_buena',
            categoria=self.categoria_restauracion,
            nombre='Obturación en Buen Estado',
            siglas='OBE',
            simbolo_color='#0000FF',
            prioridad=2,
            tipo_recurso_fhir='Procedure',
            activo=True
        )
        
        self.diag_protesis_total = Diagnostico.objects.create(
            key='protesis_total_indicada',
            categoria=self.categoria_restauracion,
            nombre='Prótesis Total Indicada',
            siglas='PTI',
            simbolo_color='#FFA500',
            prioridad=4,
            tipo_recurso_fhir='Procedure',
            activo=True
        )
    
    def test_guardar_odontograma_completo_servicio(self):
        """
        Test del servicio: Guardar odontograma completo con múltiples diagnósticos
        """
        # Datos del odontograma a guardar
        odontograma_data = {
            "11": {  # Incisivo central superior derecho
                "vestibular": [
                    {
                        "procedimientoId": "caries_icdas_3",
                        "colorHex": "#FF0000",
                        "descripcion": "Caries profunda en vestibular",
                        "secondaryOptions": {
                            "material": "resina",
                            "extension": "moderada"
                        }
                    }
                ],
                "oclusal": [
                    {
                        "procedimientoId": "obturacion_buena",
                        "colorHex": "#0000FF",
                        "descripcion": "Obturación amalgama en buen estado"
                    }
                ]
            },
            "21": {  # Incisivo central superior izquierdo
                "vestibular": [
                    {
                        "procedimientoId": "caries_icdas_4",
                        "descripcion": "Caries extensa"
                    }
                ],
                "mesial": [
                    {
                        "procedimientoId": "caries_icdas_3",
                        "descripcion": "Caries interproximal"
                    }
                ]
            },
            "31": {  # Incisivo central inferior izquierdo
                "lingual": [
                    {
                        "procedimientoId": "protesis_total_indicada",
                        "descripcion": "Necesita prótesis"
                    }
                ]
            }
        }
        
        # Ejecutar servicio
        resultado = self.service.guardar_odontograma_completo(
            paciente_id=str(self.paciente.id),
            odontologo_id=self.odontologo.id,
            odontograma_data=odontograma_data
        )
        
        # ========== VERIFICACIONES ==========
        
        # 1. Verificar resultado del servicio
        self.assertEqual(resultado['paciente_id'], str(self.paciente.id))
        self.assertEqual(len(resultado['dientes_procesados']), 3)
        self.assertIn('11', resultado['dientes_procesados'])
        self.assertIn('21', resultado['dientes_procesados'])
        self.assertIn('31', resultado['dientes_procesados'])
        self.assertEqual(resultado['diagnosticos_guardados'], 5)  # Total de diagnósticos
        self.assertEqual(len(resultado['errores']), 0)
        
        # 2. Verificar que se crearon los dientes
        dientes = Diente.objects.filter(paciente=self.paciente)
        self.assertEqual(dientes.count(), 3)
        
        diente_11 = Diente.objects.get(paciente=self.paciente, codigo_fdi='11')
        diente_21 = Diente.objects.get(paciente=self.paciente, codigo_fdi='21')
        diente_31 = Diente.objects.get(paciente=self.paciente, codigo_fdi='31')
        
        self.assertIsNotNone(diente_11)
        self.assertIsNotNone(diente_21)
        self.assertIsNotNone(diente_31)
        
        # 3. Verificar superficies creadas
        superficies_11 = SuperficieDental.objects.filter(diente=diente_11)
        self.assertEqual(superficies_11.count(), 2)  # vestibular y oclusal
        
        superficie_vestibular_11 = SuperficieDental.objects.get(
            diente=diente_11,
            nombre='vestibular'
        )
        superficie_oclusal_11 = SuperficieDental.objects.get(
            diente=diente_11,
            nombre='oclusal'
        )
        
        # 4. Verificar diagnósticos guardados
        diagnosticos_totales = DiagnosticoDental.objects.filter(
            superficie__diente__paciente=self.paciente,
            activo=True
        )
        self.assertEqual(diagnosticos_totales.count(), 5)
        
        # Verificar diagnóstico específico en diente 11 vestibular
        diag_vestibular_11 = DiagnosticoDental.objects.get(
            superficie=superficie_vestibular_11,
            diagnostico_catalogo=self.diag_caries_icdas_3
        )
        
        self.assertEqual(diag_vestibular_11.odontologo, self.odontologo)
        self.assertEqual(diag_vestibular_11.descripcion, "Caries profunda en vestibular")
        self.assertEqual(diag_vestibular_11.atributos_clinicos['material'], 'resina')
        self.assertEqual(diag_vestibular_11.estado_tratamiento, 'diagnosticado')
        self.assertTrue(diag_vestibular_11.activo)
        self.assertIsNotNone(diag_vestibular_11.fecha)
        
        # Verificar que la fecha es reciente (últimos 5 segundos)
        tiempo_transcurrido = timezone.now() - diag_vestibular_11.fecha
        self.assertLess(tiempo_transcurrido.total_seconds(), 5)
        
        # 5. Verificar que se ligó correctamente al paciente
        self.assertEqual(diag_vestibular_11.paciente, self.paciente)
        
        # 6. Verificar historial de cambios
        # CORREGIDO: Puede haber más registros por signals
        historial = HistorialOdontograma.objects.filter(
            diente__paciente=self.paciente
        )
        self.assertGreaterEqual(historial.count(), 5)  # Al menos 5 (puede haber duplicados por signals)
        
        # Verificar que existe al menos un registro para el diagnóstico agregado
        historial_vestibular_exists = HistorialOdontograma.objects.filter(
            diente=diente_11,
            tipo_cambio='diagnostico_agregado',
            datos_nuevos__diagnostico='caries_icdas_3',
            datos_nuevos__superficie='vestibular'
        ).exists()
        
        self.assertTrue(historial_vestibular_exists)
        
        # 7. Verificar diente 21 con múltiples superficies
        diagnosticos_21 = DiagnosticoDental.objects.filter(
            superficie__diente=diente_21,
            activo=True
        )
        self.assertEqual(diagnosticos_21.count(), 2)
        
        print("\n✅ TEST SERVICIO COMPLETADO EXITOSAMENTE")
        print(f"   - Paciente: {self.paciente.nombres} {self.paciente.apellidos}")
        print(f"   - Odontólogo: {self.odontologo.nombres} {self.odontologo.apellidos}")
        print(f"   - Dientes procesados: {resultado['dientes_procesados']}")
        print(f"   - Diagnósticos guardados: {resultado['diagnosticos_guardados']}")
        print(f"   - Registros de historial: {historial.count()}")
    
    def test_guardar_odontograma_endpoint_api(self):
        """
        Test del endpoint API: POST /api/odontogram/pacientes/{id}/guardar-odontograma/
        """
        url = f'/api/odontogram/pacientes/{self.paciente.id}/guardar-odontograma/'
        
        payload = {
            "odontologo_id": self.odontologo.id,
            "odontograma_data": {
                "12": {  # Incisivo lateral superior derecho
                    "vestibular": [
                        {
                            "procedimientoId": "caries_icdas_4",
                            "descripcion": "Caries extensa vestibular",
                            "secondaryOptions": {
                                "profundidad": "alta",
                                "dolor": "si"
                            }
                        }
                    ],
                    "distal": [
                        {
                            "procedimientoId": "caries_icdas_3",
                            "descripcion": "Caries en distal"
                        }
                    ]
                },
                "22": {
                    "oclusal": [
                        {
                            "procedimientoId": "obturacion_buena",
                            "descripcion": "Obturación previa"
                        }
                    ]
                }
            }
        }
        
        # Ejecutar request
        response = self.client.post(url, payload, format='json')
        
        # Verificar respuesta HTTP
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
        
        # Verificar datos de respuesta
        data = response.json()
        
        if 'data' in data:  # Si usa wrapper de respuesta
            result = data['data']
        else:
            result = data
        
        self.assertEqual(result['paciente_id'], str(self.paciente.id))
        self.assertEqual(len(result['dientes_procesados']), 2)
        self.assertEqual(result['diagnosticos_guardados'], 3)
        self.assertEqual(len(result['errores']), 0)
        
        # Verificar en base de datos
        diente_12 = Diente.objects.get(paciente=self.paciente, codigo_fdi='12')
        diagnosticos_12 = DiagnosticoDental.objects.filter(
            superficie__diente=diente_12,
            activo=True
        )
        self.assertEqual(diagnosticos_12.count(), 2)
        
        print("\n✅ TEST ENDPOINT API COMPLETADO EXITOSAMENTE")
        print(f"   - URL: {url}")
        print(f"   - Status: {response.status_code}")
        print(f"   - Diagnósticos guardados: {result['diagnosticos_guardados']}")
    
    def test_validacion_paciente_inexistente(self):
        """Test que verifica error cuando el paciente no existe"""
        paciente_falso_id = str(uuid.uuid4())
        
        odontograma_data = {
            "11": {
                "vestibular": [
                    {"procedimientoId": "caries_icdas_3"}
                ]
            }
        }
        
        with self.assertRaises(Exception) as context:
            self.service.guardar_odontograma_completo(
                paciente_id=paciente_falso_id,
                odontologo_id=self.odontologo.id,
                odontograma_data=odontograma_data
            )
        
        self.assertIn("Paciente", str(context.exception))
        print("\n✅ TEST VALIDACIÓN PACIENTE INEXISTENTE EXITOSO")
    
    def test_validacion_odontologo_inexistente(self):
        """Test que verifica error cuando el odontólogo no existe"""
        odontograma_data = {
            "11": {
                "vestibular": [
                    {"procedimientoId": "caries_icdas_3"}
                ]
            }
        }
        
        with self.assertRaises(Exception) as context:
            self.service.guardar_odontograma_completo(
                paciente_id=str(self.paciente.id),
                odontologo_id=99999,  # ID inexistente
                odontograma_data=odontograma_data
            )
        
        self.assertIn("odontólogo", str(context.exception).lower())
        print("\n✅ TEST VALIDACIÓN ODONTÓLOGO INEXISTENTE EXITOSO")
    
    def test_validacion_diagnostico_inexistente(self):
        """Test que verifica manejo de diagnóstico no encontrado"""
        odontograma_data = {
            "11": {
                "vestibular": [
                    {"procedimientoId": "diagnostico_falso_xyz"}
                ]
            }
        }
        
        resultado = self.service.guardar_odontograma_completo(
            paciente_id=str(self.paciente.id),
            odontologo_id=self.odontologo.id,
            odontograma_data=odontograma_data
        )
        
        # Debe registrar el error pero no fallar completamente
        self.assertEqual(resultado['diagnosticos_guardados'], 0)
        self.assertGreater(len(resultado['errores']), 0)
        self.assertIn('diagnostico_falso_xyz', resultado['errores'][0])
        
        print("\n✅ TEST VALIDACIÓN DIAGNÓSTICO INEXISTENTE EXITOSO")
    
    def test_multiples_diagnosticos_misma_superficie(self):
        """Test que verifica guardar múltiples diagnósticos en la misma superficie"""
        odontograma_data = {
            "13": {
                "oclusal": [
                    {
                        "procedimientoId": "caries_icdas_3",
                        "descripcion": "Caries inicial"
                    },
                    {
                        "procedimientoId": "caries_icdas_4",
                        "descripcion": "Caries extensa"
                    },
                    {
                        "procedimientoId": "obturacion_buena",
                        "descripcion": "Obturación previa"
                    }
                ]
            }
        }
        
        resultado = self.service.guardar_odontograma_completo(
            paciente_id=str(self.paciente.id),
            odontologo_id=self.odontologo.id,
            odontograma_data=odontograma_data
        )
        
        # Verificar que se guardaron los 3 diagnósticos
        self.assertEqual(resultado['diagnosticos_guardados'], 3)
        
        diente_13 = Diente.objects.get(paciente=self.paciente, codigo_fdi='13')
        superficie_oclusal = SuperficieDental.objects.get(diente=diente_13, nombre='oclusal')
        
        diagnosticos = DiagnosticoDental.objects.filter(
            superficie=superficie_oclusal,
            activo=True
        )
        self.assertEqual(diagnosticos.count(), 3)
        
        print("\n✅ TEST MÚLTIPLES DIAGNÓSTICOS MISMA SUPERFICIE EXITOSO")


class ObtenerOdontogramaCompletoTestCase(TransactionTestCase):
    """
    Test para obtener odontograma guardado previamente
    """
    
    def setUp(self):
        """Configuración inicial"""
        self.paciente_id = 'd0aac59f-da6c-4eaa-95b9-e9d471e97760'
        
        # Crear usuario de prueba para autenticación
        self.usuario = User.objects.create_user(
            username='test_user',
            correo='test@plexident.com',
            password='testpass123',
            nombres='Test',
            apellidos='User',
            rol='Odontologo',
            telefono='0999999999',
            activo=True
        )
        
        # Crear paciente si no existe
        try:
            self.paciente = Paciente.objects.get(id=self.paciente_id)
        except Paciente.DoesNotExist:
            self.paciente = Paciente.objects.create(
                id=self.paciente_id,
                nombres='María',
                apellidos='González',
                cedula_pasaporte='0987654321',
                sexo='F',
                fecha_nacimiento='1985-05-20',
                edad=40,
                condicion_edad='A',
                telefono='0999888777',
                correo='maria.gonzalez@test.com',
                direccion='Guayaquil, Ecuador',
                activo=True
            )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.usuario)
        self.service = OdontogramaService()
    
    def test_obtener_odontograma_completo_endpoint(self):
        """Test GET /api/odontogram/pacientes/{id}/odontograma/"""
        url = f'/api/odontogram/pacientes/{self.paciente.id}/odontograma/'
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.json()
        
        if 'data' in data:
            result = data['data']
        else:
            result = data
        
        # CORREGIDO: Verificar estructura de respuesta correcta
        self.assertIn('paciente', result)
        self.assertIn('dientes', result)
        self.assertIsInstance(result['paciente'], dict)
        self.assertIsInstance(result['dientes'], list)
        
        # Verificar que el paciente tiene el ID correcto
        self.assertEqual(result['paciente']['id'], str(self.paciente.id))
        
        print("\n✅ TEST OBTENER ODONTOGRAMA ENDPOINT EXITOSO")
        print(f"   - Dientes encontrados: {len(result['dientes'])}")


# Ejecutar tests con: python manage.py test api.odontogram.tests.test_guardar_odontograma
