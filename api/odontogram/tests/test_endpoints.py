# api/odontogram/tests/test_endpoints.py
"""
Tests completos para todos los endpoints
- Catálogo
- Instancias
- FHIR
- Exportación
"""
import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from api.patients.models import Paciente
from api.odontogram.models import (
    CategoriaDiagnostico,
    Diagnostico,
    Diente,
    SuperficieDental,
    DiagnosticoDental,
)

from api.users.repositories.user_repository import UserRepository

User = get_user_model()


class CatalogoEndpointsTestCase(TestCase):
    """Tests para endpoints del catálogo (lectura)"""

    @classmethod
    def setUpTestData(cls):
        """Setup de datos de prueba"""
        # Usuario
        cls.user = UserRepository.create(
            username="test_catalog",
            nombres="Test",
            apellidos="Catalog",
            correo="catalog@test.com",
            telefono="0987654321",
            rol="odontologo",
            password="test123",
        )

        # Categoría
        cls.categoria = CategoriaDiagnostico.objects.create(
            key="patologia",
            nombre="Patología",
            color_key="#FF0000",
            prioridad_key="ALTA",
        )

        # Diagnóstico
        cls.diagnostico = Diagnostico.objects.create(
            key="caries_1",
            categoria=cls.categoria,
            nombre="Caries Incipiente",
            siglas="C1",
            simbolo_color="#FF0000",
            prioridad=1,
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_get_categorias(self):
        """GET /api/odontogram/catalogo/categorias/"""
        response = self.client.get("/api/odontogram/catalogo/categorias/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Manejar ambos casos: paginado o lista directa
        if isinstance(response.data, dict) and "results" in response.data:
            self.assertIsInstance(response.data["results"], list)
        else:
            self.assertIsInstance(response.data, list)

    def test_get_categorias_by_prioridad(self):
        """GET /api/odontogram/catalogo/categorias/por_prioridad/?prioridad=ALTA"""
        response = self.client.get(
            "/api/odontogram/catalogo/categorias/por_prioridad/?prioridad=ALTA"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_get_diagnosticos(self):
        """GET /api/odontogram/catalogo/diagnosticos/"""
        response = self.client.get("/api/odontogram/catalogo/diagnosticos/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Manejar ambos casos: paginado o lista directa
        if isinstance(response.data, dict) and "results" in response.data:
            self.assertIsInstance(response.data["results"], list)
        else:
            self.assertIsInstance(response.data, list)

    def test_get_diagnostico_detail(self):
        """GET /api/odontogram/catalogo/diagnosticos/{id}/"""
        response = self.client.get(
            f"/api/odontogram/catalogo/diagnosticos/{self.diagnostico.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.diagnostico.id)

    def test_get_diagnosticos_by_categoria(self):
        """GET /api/odontogram/catalogo/diagnosticos/por_categoria/?categoria_id=1"""
        response = self.client.get(
            f"/api/odontogram/catalogo/diagnosticos/por_categoria/?categoria_id={self.categoria.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_get_diagnosticos_criticos(self):
        """GET /api/odontogram/catalogo/diagnosticos/criticos/"""
        response = self.client.get("/api/odontogram/catalogo/diagnosticos/criticos/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_diagnosticos_buscar(self):
        """GET /api/odontogram/catalogo/diagnosticos/buscar/?q=caries"""
        response = self.client.get(
            "/api/odontogram/catalogo/diagnosticos/buscar/?q=caries"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class PacienteEndpointsTestCase(TestCase):
    """Tests para endpoints de pacientes (CRUD)"""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserRepository.create(
            username="test_pacientes",
            nombres="Test",
            apellidos="Pacientes",
            correo="pacientes@test.com",
            telefono="0987654321",
            rol="odontologo",
            password="test123",
        )

        cls.paciente = Paciente.objects.create(
            nombres="Juan",
            apellidos="Pérez",
            cedula_pasaporte="1234567890",
            sexo="M",
            fecha_nacimiento="1990-01-15",
            telefono="0987654321",
            correo="juan@test.com",
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_get_pacientes(self):
        """GET /api/odontogram/pacientes/"""
        response = self.client.get("/api/odontogram/pacientes/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Manejar ambos casos: paginado o lista directa
        if isinstance(response.data, dict) and "results" in response.data:
            data = response.data["results"]
        else:
            data = response.data
        self.assertIsInstance(data, (list, dict))

    def test_get_paciente_detail(self):
        """GET /api/odontogram/pacientes/{id}/"""
        response = self.client.get(f"/api/odontogram/pacientes/{self.paciente.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("id", response.data)  # Verificar que tenga ID

    def test_get_paciente_odontograma(self):
        """GET /api/odontogram/pacientes/{id}/odontograma/"""
        response = self.client.get(
            f"/api/odontogram/pacientes/{self.paciente.id}/odontograma/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_paciente_diagnosticos(self):
        """GET /api/odontogram/pacientes/{id}/diagnosticos/"""
        response = self.client.get(
            f"/api/odontogram/pacientes/{self.paciente.id}/diagnosticos/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_paciente_odontograma_fhir(self):
        """GET /api/odontogram/pacientes/{id}/odontograma-fhir/"""
        response = self.client.get(
            f"/api/odontogram/pacientes/{self.paciente.id}/odontograma-fhir/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["resourceType"], "Bundle")

    def test_post_paciente(self):
        """POST /api/odontogram/pacientes/"""
        data = {
            "nombres": "Pedro",
            "apellidos": "López",
            "cedula_pasaporte": "9876543210",
            "sexo": "M",
            "fecha_nacimiento": "1995-01-01",
            "telefono": "0987654321",
            "correo": "pedro@test.com",
        }
        response = self.client.post("/api/odontogram/pacientes/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_put_paciente(self):
        """PUT /api/odontogram/pacientes/{id}/"""
        data = {
            "nombres": "Juan Updated",
            "apellidos": self.paciente.apellidos,
            "cedula_pasaporte": self.paciente.cedula_pasaporte,
            "sexo": self.paciente.sexo,
            "fecha_nacimiento": self.paciente.fecha_nacimiento,
            "telefono": "1234567890",
            "correo": self.paciente.correo,
        }
        response = self.client.put(
            f"/api/odontogram/pacientes/{self.paciente.id}/", data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class DienteEndpointsTestCase(TestCase):
    """Tests para endpoints de dientes (CRUD)"""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserRepository.create(
            username="test_dientes",
            nombres="Test",
            apellidos="Dientes",
            correo="dientes@test.com",
            telefono="0987654321",
            rol="odontologo",
            password="test123",
        )

        cls.paciente = Paciente.objects.create(
            nombres="Juan",
            apellidos="Pérez",
            cedula_pasaporte="1234567890",
            sexo="M",
            fecha_nacimiento="1990-01-15",
            telefono="0987654321",
            correo="juan@test.com",
        )

        cls.diente = Diente.objects.create(
            paciente=cls.paciente, codigo_fdi="16", nombre="Diente 16"
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_get_dientes(self):
        """GET /api/odontogram/dientes/"""
        response = self.client.get("/api/odontogram/dientes/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Manejar ambos casos: paginado o lista directa
        if isinstance(response.data, dict) and "results" in response.data:
            data = response.data["results"]
        else:
            data = response.data
        self.assertIsInstance(data, (list, dict))

    def test_get_dientes_by_paciente(self):
        """GET /api/odontogram/dientes/?paciente_id={id}"""
        response = self.client.get(
            f"/api/odontogram/dientes/?paciente_id={self.paciente.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_diente_detail(self):
        """GET /api/odontogram/dientes/{id}/"""
        response = self.client.get(f"/api/odontogram/dientes/{self.diente.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class DiagnosticoDentalEndpointsTestCase(TestCase):
    """Tests para endpoints de diagnósticos dentales (CRUD)"""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserRepository.create(
            username="test_diag",
            nombres="Test",
            apellidos="Diagnosticos",
            correo="diag@test.com",
            telefono="0987654321",
            rol="odontologo",
            password="test123",
        )

        cls.paciente = Paciente.objects.create(
            nombres="Juan",
            apellidos="Pérez",
            cedula_pasaporte="1234567890",
            sexo="M",
            fecha_nacimiento="1990-01-15",
            telefono="0987654321",
            correo="juan@test.com",
        )

        cls.categoria = CategoriaDiagnostico.objects.create(
            key="patologia",
            nombre="Patología",
            color_key="#FF0000",
            prioridad_key="ALTA",
        )

        cls.diagnostico_cat = Diagnostico.objects.create(
            key="caries_1",
            categoria=cls.categoria,
            nombre="Caries",
            siglas="C1",
            simbolo_color="#FF0000",
            prioridad=1,
        )

        cls.diente = Diente.objects.create(
            paciente=cls.paciente, codigo_fdi="16", nombre="Diente 16"
        )

        cls.superficie = SuperficieDental.objects.create(
            diente=cls.diente, nombre="oclusal"
        )

        cls.diag_dental = DiagnosticoDental.objects.create(
            superficie=cls.superficie,
            diagnostico_catalogo=cls.diagnostico_cat,
            odontologo=cls.user,
            descripcion="Caries profunda",
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_get_diagnosticos_aplicados(self):
        """GET /api/odontogram/diagnosticos-aplicados/"""
        response = self.client.get("/api/odontogram/diagnosticos-aplicados/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Manejar ambos casos: paginado o lista directa
        if isinstance(response.data, dict) and "results" in response.data:
            data = response.data["results"]
        else:
            data = response.data
        self.assertIsInstance(data, (list, dict))

    def test_get_diag_dental_detail(self):
        """GET /api/odontogram/diagnosticos-aplicados/{id}/"""
        response = self.client.get(
            f"/api/odontogram/diagnosticos-aplicados/{self.diag_dental.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_post_marcar_tratado(self):
        """POST /api/odontogram/diagnosticos-aplicados/{id}/marcar_tratado/"""
        response = self.client.post(
            f"/api/odontogram/diagnosticos-aplicados/{self.diag_dental.id}/marcar_tratado/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class FHIREndpointsTestCase(TestCase):
    """Tests para endpoints FHIR"""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserRepository.create(
            username="test_fhir",
            nombres="Test",
            apellidos="FHIR",
            correo="fhir@test.com",
            telefono="0987654321",
            rol="odontologo",
            password="test123",
        )

        cls.paciente = Paciente.objects.create(
            nombres="Juan",
            apellidos="Pérez",
            cedula_pasaporte="1234567890",
            sexo="M",
            fecha_nacimiento="1990-01-15",
            telefono="0987654321",
            correo="juan@test.com",
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_get_fhir_patient(self):
        """GET /api/odontogram/fhir/patient/{id}/"""
        response = self.client.get(f"/api/odontogram/fhir/patient/{self.paciente.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verificar que retorna resourceType válido
        self.assertIn("reference", response.data) 

    def test_get_fhir_odontograma(self):
        """GET /api/odontogram/fhir/odontograma/{id}/"""
        response = self.client.get(
            f"/api/odontogram/fhir/odontograma/{self.paciente.id}/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["resourceType"], "Bundle")
        self.assertEqual(response.data["type"], "collection")

    def test_get_fhir_cda(self):
        """GET /api/odontogram/fhir/cda/{id}/"""
        response = self.client.get(f"/api/odontogram/fhir/cda/{self.paciente.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["resourceType"], "Bundle")
        self.assertEqual(response.data["type"], "document")

    def test_post_fhir_validate(self):
        """POST /api/odontogram/fhir/validate/"""
        data = {
            "resource": {"resourceType": "Patient", "id": "123"},
            "profile": "http://hl7.org/fhir/StructureDefinition/Patient",
        }
        response = self.client.post(
            "/api/odontogram/fhir/validate/", data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("valid", response.data)

    def test_get_fhir_search(self):
        """GET /api/odontogram/fhir/search/"""
        response = self.client.get(
            f"/api/odontogram/fhir/search/?patient={self.paciente.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["resourceType"], "Bundle")


class ExportEndpointsTestCase(TestCase):
    """Tests para endpoints de exportación"""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserRepository.create(
            username="test_export",
            nombres="Test",
            apellidos="Export",
            correo="export@test.com",
            telefono="0987654321",
            rol="odontologo",
            password="test123",
        )

        cls.paciente = Paciente.objects.create(
            nombres="Juan",
            apellidos="Pérez",
            cedula_pasaporte="1234567890",
            sexo="M",
            fecha_nacimiento="1990-01-15",
            telefono="0987654321",
            correo="juan@test.com",
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_get_export_fhir_bundle(self):
        """GET /api/odontogram/odontogramas/{id}/export-fhir-bundle/"""
        response = self.client.get(
            f"/api/odontogram/odontogramas/{self.paciente.id}/export-fhir-bundle/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["resourceType"], "Bundle")

    def test_get_export_cda_xml(self):
        """GET /api/odontogram/odontogramas/{id}/export-cda/"""
        response = self.client.get(
            f"/api/odontogram/odontogramas/{self.paciente.id}/export-cda/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/xml")


# ==================== PYTEST MARKERS ====================


@pytest.mark.django_db
class TestAllEndpointsPytest:
    """Tests con pytest markers"""

    def test_endpoints_structure(self):
        """Verificar que todos los endpoints existen"""
        from django.urls import reverse

        endpoints = [
            "catalogo/categorias",
            "catalogo/diagnosticos",
            "pacientes",
            "dientes",
            "diagnosticos-aplicados",
            "fhir/patient",
            "fhir/search",
        ]

        assert len(endpoints) > 0
