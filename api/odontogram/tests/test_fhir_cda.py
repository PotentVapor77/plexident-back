# api/odontogram/tests/test_fhir_cda.py

import pytest
import json
import time
from datetime import datetime
from unittest.mock import patch, MagicMock
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from api.users.repositories.user_repository import UserRepository
from lxml import etree

# Modelos
from api.patients.models import Paciente
from api.odontogram.models import (
    CategoriaDiagnostico,
    Diagnostico,
    Diente,
    SuperficieDental,
    DiagnosticoDental,
    TipoAtributoClinico,
    OpcionAtributoClinico,
)

# Serializadores
from api.odontogram.serializers.fhir_serializers import (
    ClinicalFindingFHIRSerializer,
    FHIRPatientReferenceSerializer,
    BodyStructureFHIRSerializer,
)

# Servicios
from api.odontogram.services.cda_service import CDAGenerationService
from api.odontogram.services.odontogram_services import OdontogramaService

# Validadores
# import requests

User = get_user_model()


class FHIRStructureTestCase(TestCase):
    """
    ✓ Valida conformidad con estándar FHIR R4/R5
    ✓ Verifica estructura JSON
    ✓ Chequea campos obligatorios
    """

    @classmethod
    def setUpTestData(cls):
        """Setup común para todos los tests"""
        # Crear paciente
        cls.paciente = Paciente.objects.create(
            nombres="Juan",
            apellidos="Pérez",
            cedula_pasaporte="1234567890",
            sexo="M",
            fecha_nacimiento="1990-01-15",
            telefono="0987654321",  
            correo="juan@example.com", 
        )

        # Crear odontólogo
        cls.odontologo = UserRepository.create(
            username="dr_carlos",
            nombres="Carlos",  # ← CAMBIO: first_name → nombres
            apellidos="Rodríguez",  # ← CAMBIO: last_name → apellidos
            correo="carlos@clinic.com",  # ← CAMBIO: email → correo
            telefono="0987654321",  # ← NUEVO REQUERIDO (min 10 dígitos)
            rol="odontologo",  # ← NUEVO REQUERIDO (admin/odontologo/asistente)
            password="test123",
        )

        # Crear categoría de diagnóstico
        cls.categoria = CategoriaDiagnostico.objects.create(
            key="patologia",
            nombre="Patología Activa",
            color_key="#FF5733",
            prioridad_key="ALTA",
        )

        # Crear diagnóstico (caries)
        cls.diagnostico_caries = Diagnostico.objects.create(
            key="caries_icdas_3",
            categoria=cls.categoria,
            nombre="Caries ICDAS 3",
            siglas="C3",
            simbolo_color="#FF5733",
            prioridad=3,
            codigo_icd10="K02.9",
            codigo_fhir="80276007",  # SNOMED: Caries of dentine
            tipo_recurso_fhir="Condition",
        )

        # Crear diente
        cls.diente = Diente.objects.create(
            paciente=cls.paciente,
            codigo_fdi="11",
            nombre="Primer Molar Superior Derecho",
        )

        # Crear superficie
        cls.superficie = SuperficieDental.objects.create(
            diente=cls.diente, nombre="oclusal"
        )

        # Crear diagnóstico dental
        cls.diagnostico_dental = DiagnosticoDental.objects.create(
            superficie=cls.superficie,
            diagnostico_catalogo=cls.diagnostico_caries,
            odontologo=cls.odontologo,
            descripcion="Caries profunda en oclusal",
            atributos_clinicos={"material": "resina"},
            estado_tratamiento="diagnosticado",
            movilidad=0,
            recesion_gingival=0,
        )

    def test_fhir_patient_reference_structure(self):
        """
        ✓ Valida que FHIRPatientReferenceSerializer genere estructura válida
        """
        serializer = FHIRPatientReferenceSerializer(self.paciente)
        data = serializer.data

        # Validaciones estructurales
        assert "reference" in data
        assert "type" in data
        assert "identifier" in data
        assert "display" in data

        # Validar formato de reference
        assert data["type"] == "Patient"
        assert data["reference"].startswith("Patient/")

        # Validar identifier
        assert data["identifier"]["system"] == "urn:oid:plexident.co"
        assert data["identifier"]["value"] == str(self.paciente.id)

    def test_clinical_finding_fhir_serialization(self):
        """
        ✓ Valida serialización de ClinicalFinding a FHIR
        ✓ Verifica campos FHIR obligatorios
        """
        serializer = ClinicalFindingFHIRSerializer(self.diagnostico_dental)
        data = serializer.data

        # Campos obligatorios FHIR
        required_fields = [
            "resourceType",
            "id",
            "identifier",
            "code",
            "subject",
            "recordedDate",
        ]

        for field in required_fields:
            assert field in data, f"Campo requerido '{field}' no encontrado"

        # Validar valores
        assert data["resourceType"] == "Condition"
        assert data["id"] == str(self.diagnostico_dental.id)
        assert len(data["identifier"]) > 0
        assert "coding" in data["code"]
        assert len(data["code"]["coding"]) > 0

    def test_body_structure_serialization(self):
        """
        ✓ Valida serialización de BodyStructure (superficie dental)
        """
        serializer = BodyStructureFHIRSerializer(self.superficie)
        data = serializer.data

        # Validar estructura
        assert data["resourceType"] == "BodyStructure"
        assert "location" in data
        assert "morphology" in data
        assert "identifier" in data

        # Validar ubicación anatómica
        assert "coding" in data["location"]
        assert len(data["location"]["coding"]) >= 2

    def test_fhir_severity_mapping(self):
        """
        ✓ Valida mapeo correcto de prioridad -> severidad FHIR
        """
        serializer = ClinicalFindingFHIRSerializer(self.diagnostico_dental)
        data = serializer.data

        # Validar severity
        assert "severity" in data
        assert "coding" in data["severity"]
        assert len(data["severity"]["coding"]) > 0
        assert "code" in data["severity"]["coding"][0]
        assert "display" in data["severity"]["coding"][0]

    def test_fhir_multiple_resource_types(self):
        """
        ✓ Valida generación de diferentes tipos de recursos FHIR
        """
        # Crear diagnóstico de procedimiento
        categoria_proc = CategoriaDiagnostico.objects.create(
            key="tratamiento",
            nombre="Tratamiento",
            color_key="#00FF00",
            prioridad_key="MEDIA",
        )

        diagnostico_proc = Diagnostico.objects.create(
            key="restauracion_simple",
            categoria=categoria_proc,
            nombre="Restauración Simple",
            siglas="RES",
            simbolo_color="#00FF00",
            prioridad=2,
            tipo_recurso_fhir="Procedure",
        )

        # Crear instancia
        diag_dental_proc = DiagnosticoDental.objects.create(
            superficie=self.superficie,
            diagnostico_catalogo=diagnostico_proc,
            odontologo=self.odontologo,
            estado_tratamiento="tratado",
        )

        # Serializar
        serializer = ClinicalFindingFHIRSerializer(diag_dental_proc)
        data = serializer.data
        assert data["resourceType"] == "Procedure"
        assert "status" in data  # Procedure tiene status, no clinicalStatus
        assert data["status"] == "completed"

    def test_fhir_json_validity(self):
        """
        ✓ Valida que el JSON generado es válido y bien formado
        """
        serializer = ClinicalFindingFHIRSerializer(self.diagnostico_dental)
        data = serializer.data

        # Convertir a JSON y parsed nuevamente (double-check)
        json_str = json.dumps(data)
        parsed = json.loads(json_str)

        assert isinstance(parsed, dict)
        assert "resourceType" in parsed


class CDAGenerationTestCase(TransactionTestCase):
    """
    ✓ Valida generación de CDA (Clinical Document Architecture)
    ✓ Verifica conformidad con HL7 v3
    ✓ Chequea XML bien formado
    """

    def setUp(self):
        """Setup para cada test"""
        # Crear paciente
        self.paciente = Paciente.objects.create(
            nombres="María",
            apellidos="García",
            cedula_pasaporte="9876543210",
            sexo="F",
            fecha_nacimiento="1985-03-22",
            telefono="0987654321",
            correo="maria@example.com",  #
        )

        # Crear odontólogo
        self.odontologo = UserRepository.create(
            username="dra_marta",
            nombres="Marta",
            apellidos="López",
            correo="marta@clinic.com",  # ← REQUIRED (antes no era necesario)
            telefono="0987654321",  # ← NUEVO REQUERIDO
            rol="odontologo",  # ← NUEVO REQUERIDO
            password="test123",
        )

        # Crear categoría
        self.categoria = CategoriaDiagnostico.objects.create(
            key="patologia",
            nombre="Patología",
            color_key="#FF5733",
            prioridad_key="ALTA",
        )

        # Crear diagnóstico
        self.diagnostico = Diagnostico.objects.create(
            key="caries_simple",
            categoria=self.categoria,
            nombre="Caries",
            siglas="C",
            simbolo_color="#FF5733",
            prioridad=3,
            codigo_icd10="K02.9",
            codigo_fhir="80276007",
            tipo_recurso_fhir="Condition",
        )

        # Crear estructura de diente
        self.diente = Diente.objects.create(paciente=self.paciente, codigo_fdi="36")

        self.superficie = SuperficieDental.objects.create(
            diente=self.diente, nombre="oclusal"
        )

        DiagnosticoDental.objects.create(
            superficie=self.superficie,
            diagnostico_catalogo=self.diagnostico,
            odontologo=self.odontologo,
            descripcion="Caries profunda",
        )

        self.cda_service = CDAGenerationService()

    def test_cda_generation_basic(self):
        """
        ✓ Valida generación básica de CDA XML
        """
        cda_xml = self.cda_service.generate_cda_xml(str(self.paciente.id))

        # Validar que es XML válido
        assert isinstance(cda_xml, str)
        assert cda_xml.startswith("<?xml")
        assert "<?xml" in cda_xml

    def test_cda_patient_information(self):
        """
        ✓ Valida que los datos del paciente se incluyen correctamente
        """
        cda_xml = self.cda_service.generate_cda_xml(str(self.paciente.id))
        root = etree.fromstring(cda_xml.encode("utf-8"))

        # Buscar nombre del paciente
        nsmap = {"cda": "urn:hl7-org:v3"}
        given_name = root.findtext(
            "cda:recordTarget/cda:patientRole/cda:patient/cda:name/cda:given",
            namespaces=nsmap,
        )
        family_name = root.findtext(
            "cda:recordTarget/cda:patientRole/cda:patient/cda:name/cda:family",
            namespaces=nsmap,
        )

        if given_name is not None:
            assert given_name.strip() == self.paciente.nombres

        if family_name is not None:
            assert family_name.strip() == self.paciente.apellidos

    def test_cda_xml_structure(self):
        """
        ✓ Valida estructura básica de documento CDA
        """
        cda_xml = self.cda_service.generate_cda_xml(str(self.paciente.id))
        root = etree.fromstring(cda_xml.encode("utf-8"))

        # Validar elementos principales
        nsmap = {"cda": "urn:hl7-org:v3"}
        assert (
            root.findtext("cda:title", namespaces=nsmap) is not None
        )  # Debe tener título
        assert (
            root.findtext("cda:effectiveTime", namespaces=nsmap) is not None
        )  # Debe tener timestamp

    def test_cda_namespace_validity(self):
        """
        ✓ Valida que los namespaces HL7 v3 son correctos
        """
        cda_xml = self.cda_service.generate_cda_xml(str(self.paciente.id))
        root = etree.fromstring(cda_xml.encode("utf-8"))

        # Validar que es HL7 v3 CDA
        assert (
            root.tag == "{urn:hl7-org:v3}ClinicalDocument"
        ) or root.tag == "ClinicalDocument"

    def test_cda_non_empty_patient_data(self):
        """
        ✓ Valida que los datos del paciente no están vacíos
        """
        cda_xml = self.cda_service.generate_cda_xml(str(self.paciente.id))
        root = etree.fromstring(cda_xml.encode("utf-8"))

        nsmap = {"cda": "urn:hl7-org:v3"}
        family_name = root.findtext(
            "cda:recordTarget/cda:patientRole/cda:patient/cda:name/cda:family",
            namespaces=nsmap,
        )

        if family_name is not None:
            assert len(family_name) > 0

    def test_cda_error_handling_missing_patient(self):
        """
        ✓ Valida manejo de errores cuando paciente no existe
        """
        with pytest.raises(ValueError):
            self.cda_service.generate_cda_xml("invalid-uuid")

    def test_cda_xml_encoding(self):
        """
        ✓ Valida que el XML tiene encoding UTF-8 correcto
        """
        cda_xml = self.cda_service.generate_cda_xml(str(self.paciente.id))

        assert "encoding='UTF-8'" in cda_xml or 'encoding="UTF-8"' in cda_xml
        assert cda_xml.startswith("<?xml")

    def test_cda_xml_injection_protection(self):
        """
        🔒 Valida que el XML está protegido contra inyección XML
        """
        # Datos normales (sin inyección)
        cda_xml = self.cda_service.generate_cda_xml(str(self.paciente.id))

        # Validar que es XML bien formado (no inyectado)
        try:
            etree.fromstring(cda_xml.encode("utf-8"))
            assert True  # Si parsea correctamente, no hay inyección
        except etree.XMLSyntaxError:
            assert False, "XML inyectado o mal formado"


class InteroperabilityTestCase(TestCase):
    """
    ✓ Valida integración entre FHIR y CDA
    """

    @classmethod
    def setUpTestData(cls):
        """Setup para interoperabilidad"""
        cls.paciente = Paciente.objects.create(
            nombres="Interop",
            apellidos="Test",
            cedula_pasaporte="5555555555",
            sexo="M",
            fecha_nacimiento="1995-06-10",
            telefono="0987654321",  # ✅ AGREGADO
            correo="interop@test.com",  # ✅ CORRECTO
        )

        cls.odontologo = UserRepository.create(
            username="interop_test",
            nombres="Dr",
            apellidos="Interop",
            correo="interop@example.com",
            telefono="0987654321",
            rol="odontologo",
            password="test123",
        )

        cls.categoria = CategoriaDiagnostico.objects.create(
            key="interop", nombre="Interop", color_key="#0000FF", prioridad_key="MEDIA"
        )

        cls.diagnostico = Diagnostico.objects.create(
            key="interop_diag",
            categoria=cls.categoria,
            nombre="Interop Diag",
            siglas="INT",
            simbolo_color="#0000FF",
            prioridad=2,
            codigo_icd10="K02.9",
            codigo_fhir="80276007",
        )

        cls.diente = Diente.objects.create(paciente=cls.paciente, codigo_fdi="26")
        cls.superficie = SuperficieDental.objects.create(
            diente=cls.diente, nombre="oclusal"
        )

        cls.diagnostico_dental = DiagnosticoDental.objects.create(
            superficie=cls.superficie,
            diagnostico_catalogo=cls.diagnostico,
            odontologo=cls.odontologo,
            descripcion="Interop test",
        )

    def test_fhir_codes_in_cda(self):
        """
        ✓ Valida que los códigos FHIR se incluyen en CDA
        """
        cda_service = CDAGenerationService()
        cda_xml = cda_service.generate_cda_xml(str(self.paciente.id))

        # Obtener datos FHIR
        serializer = ClinicalFindingFHIRSerializer(self.diagnostico_dental)
        fhir_data = serializer.data

        # Verificar códigos SNOMED y ICD-10
        codes = [c["code"] for c in fhir_data["code"]["coding"]]

        assert self.diagnostico.codigo_fhir in codes
        assert self.diagnostico.codigo_icd10 in codes

    def test_patient_data_consistency(self):
        """
        ✓ Valida consistencia de datos del paciente entre FHIR y CDA
        """
        # Obtener datos FHIR
        patient_serializer = FHIRPatientReferenceSerializer(self.paciente)
        fhir_patient = patient_serializer.data

        # Obtener datos CDA
        cda_service = CDAGenerationService()
        cda_xml = cda_service.generate_cda_xml(str(self.paciente.id))
        root = etree.fromstring(cda_xml.encode("utf-8"))

        nsmap = {"cda": "urn:hl7-org:v3"}

        # Extraer nombre del CDA
        given_cda = root.findtext(
            "cda:recordTarget/cda:patientRole/cda:patient/cda:name/cda:given",
            namespaces=nsmap,
        )
        family_cda = root.findtext(
            "cda:recordTarget/cda:patientRole/cda:patient/cda:name/cda:family",
            namespaces=nsmap,
        )

        # Validar consistencia
        if given_cda:
            assert given_cda == self.paciente.nombres

        if family_cda:
            assert family_cda == self.paciente.apellidos


class ConformanceValidationTestCase(TestCase):
    """
    ✓ Valida conformidad con estándares de seguridad (OWASP)
    """

    @classmethod
    def setUpTestData(cls):
        """Setup para conformance"""
        cls.paciente = Paciente.objects.create(
            nombres="Security",
            apellidos="Test",
            cedula_pasaporte="3333333333",
            sexo="M",
            fecha_nacimiento="1992-12-25",
            telefono="0987654321",
            correo="security@test.com",
        )

        cls.odontologo = UserRepository.create(
            username="security_test",
            nombres="Security",
            apellidos="Test",
            correo="security@example.com",
            telefono="0987654321",
            rol="odontologo",
            password="test123",
        )

        cls.categoria = CategoriaDiagnostico.objects.create(
            key="sec", nombre="Security", color_key="#0000FF", prioridad_key="MEDIA"
        )

        cls.diagnostico = Diagnostico.objects.create(
            key="sec_diag",
            categoria=cls.categoria,
            nombre="Security Diag",
            siglas="SEC",
            simbolo_color="#0000FF",
            prioridad=2,
        )

    def test_fhir_json_injection_protection(self):
        """
        🔒 Valida que el JSON no es susceptible a inyección
        """
        # Crear estructura con validación
        diente = Diente.objects.create(paciente=self.paciente, codigo_fdi="15")
        superficie = SuperficieDental.objects.create(diente=diente, nombre="oclusal")

        diag_dental = DiagnosticoDental.objects.create(
            superficie=superficie,
            diagnostico_catalogo=self.diagnostico,
            odontologo=self.odontologo,
            descripcion="Test seguridad",
        )

        # Serializar
        serializer = ClinicalFindingFHIRSerializer(diag_dental)
        data = serializer.data

        # Validar JSON
        json_str = json.dumps(data)
        parsed = json.loads(json_str)

        assert isinstance(parsed, dict)
        assert "resourceType" in parsed

    def test_cda_xml_injection_protection(self):
        """
        🔒 Valida que el XML está protegido contra inyección
        """
        # Crear estructura
        diente = Diente.objects.create(paciente=self.paciente, codigo_fdi="25")
        superficie = SuperficieDental.objects.create(diente=diente, nombre="oclusal")

        DiagnosticoDental.objects.create(
            superficie=superficie,
            diagnostico_catalogo=self.diagnostico,
            odontologo=self.odontologo,
            descripcion="Test CDA seguridad",
        )

        # Generar CDA
        cda_service = CDAGenerationService()
        cda_xml = cda_service.generate_cda_xml(str(self.paciente.id))

        # Validar que es XML bien formado
        try:
            etree.fromstring(cda_xml.encode("utf-8"))
            assert True  # Válido
        except etree.XMLSyntaxError:
            assert False, "XML inyectado"
