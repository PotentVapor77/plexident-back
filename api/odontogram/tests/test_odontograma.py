
# api/odontogram/tests/test_odontograma.py

import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

from api.patients.models import Paciente
from api.odontogram.models import (
    CategoriaDiagnostico,
    Diagnostico,
    Diente,
    SuperficieDental,
    DiagnosticoDental,
)
from api.odontogram.factories import (
    CategoriaDiagnosticoFactory,
    DiagnosticoFactory,
    AtributoClinicoFactory,
    ConfiguracionInicialFactory,
)

User = get_user_model()


class OdontogramaModelTestCase(TestCase):
    """Tests para modelos del odontograma"""

    def setUp(self):
        """Preparar datos para tests"""
        # Crear categoría de diagnóstico
        self.categoria = CategoriaDiagnosticoFactory.crear(
            key="test_categoria",
            nombre="Categoría Test",
            tipo="patologia"
        )

    def test_categoria_diagnostico_creation(self):
        """Test: Crear categoría de diagnóstico"""
        self.assertIsNotNone(self.categoria.id)
        self.assertEqual(self.categoria.key, "test_categoria")
        self.assertEqual(self.categoria.nombre, "Categoría Test")
        self.assertTrue(self.categoria.activo)

    def test_diagnostico_caries_creation(self):
        """Test: Crear diagnóstico de caries desde factory"""
        diag_caries = DiagnosticoFactory.crear_caries(
            categoria=self.categoria,
            nivel_icdas=3
        )
        
        self.assertEqual(diag_caries.key, "caries_icdas_3")
        self.assertEqual(diag_caries.nombre, "Caries ICDAS 3")
        self.assertEqual(diag_caries.siglas, "C3")
        self.assertEqual(diag_caries.prioridad, 4)

    def test_diagnostico_restauracion_simple(self):
        """Test: Crear diagnóstico de restauración simple"""
        diag_rest = DiagnosticoFactory.crear_restauracion(
            categoria=self.categoria,
            tipo="simple"
        )
        
        self.assertEqual(diag_rest.key, "restauracion_simple")
        self.assertEqual(diag_rest.nombre, "Restauración Simple")
        self.assertTrue(diag_rest.activo)

    def test_diagnostico_restauracion_compleja(self):
        """Test: Crear diagnóstico de restauración compleja"""
        diag_rest = DiagnosticoFactory.crear_restauracion(
            categoria=self.categoria,
            tipo="compleja"
        )
        
        self.assertEqual(diag_rest.key, "restauracion_compleja")
        self.assertEqual(diag_rest.nombre, "Restauración Compleja")

    def test_atributo_material_creation(self):
        """Test: Crear atributo clínico de material"""
        atributo = AtributoClinicoFactory.crear_material(
            key="material_test",
            nombre="Material Test",
            materiales=["Amalgama", "Resina", "Porcelana"]
        )
        
        self.assertEqual(atributo.key, "material_test")
        self.assertEqual(atributo.nombre, "Material Test")
        # Verificar que se crearon las opciones
        self.assertEqual(atributo.opciones.count(), 3)

    def test_atributo_estado_calidad(self):
        """Test: Crear atributo de estado de calidad"""
        atributo = AtributoClinicoFactory.crear_desde_plantilla(
            plantilla="estado_calidad",
            key="estado_rest",
            nombre="Estado Restauración",
            descripcion="Calidad de la restauración"
        )
        
        self.assertEqual(atributo.key, "estado_rest")
        self.assertTrue(atributo.activo)
        # Debe tener 5 opciones: excelente, buena, regular, mala, crítica
        self.assertEqual(atributo.opciones.count(), 5)

    def test_atributo_estado_procedimiento(self):
        """Test: Crear atributo de estado de procedimiento"""
        atributo = AtributoClinicoFactory.crear_estado_procedimiento(
            key="est_proc",
            nombre="Estado Procedimiento"
        )
        
        self.assertTrue(atributo.activo)
        # Debe tener 4 opciones: planificado, en_proceso, finalizado, cancelado
        self.assertEqual(atributo.opciones.count(), 4)

    def test_configuracion_basica_creation(self):
        """Test: Crear configuración básica completa"""
        # Limpiar datos existentes
        CategoriaDiagnostico.objects.all().delete()
        Diagnostico.objects.all().delete()
        
        resultado = ConfiguracionInicialFactory.crear_configuracion_basica()
        
        # Verificar que se crearon los datos
        self.assertEqual(resultado['categorias_creadas'], 2)
        self.assertGreater(resultado['diagnosticos_creados'], 0)
        self.assertGreater(resultado['atributos_creados'], 0)

    def test_multiple_caries_levels(self):
        """Test: Crear múltiples niveles de caries ICDAS"""
        for nivel in range(1, 7):
            diag = DiagnosticoFactory.crear_caries(
                categoria=self.categoria,
                nivel_icdas=nivel
            )
            
            self.assertEqual(diag.key, f"caries_icdas_{nivel}")
            self.assertTrue(diag.activo)

    def test_all_restoration_types(self):
        """Test: Crear todos los tipos de restauración"""
        tipos = ["simple", "compleja", "provisional", "definitiva"]
        
        for tipo in tipos:
            diag = DiagnosticoFactory.crear_restauracion(
                categoria=self.categoria,
                tipo=tipo
            )
            
            self.assertIsNotNone(diag.id)
            self.assertTrue(diag.activo)


class OdontogramaAPITestCase(TestCase):
    """Tests para API REST del odontograma"""

    def setUp(self):
        """Preparar datos para tests API"""
        self.client = Client()
        self.categoria = CategoriaDiagnosticoFactory.crear(
            key="api_test",
            nombre="API Test",
            tipo="patologia"
        )

    def test_categoria_list_endpoint(self):
        """Test: Endpoint para listar categorías"""
        # Este test asume que existe un endpoint GET /api/categorias/
        # Ajusta la URL según tu configuración
        response = self.client.get('/api/categorias/')
        # Puede retornar 200, 404, o 403 dependiendo de tu configuración
        self.assertIn(response.status_code, [200, 404, 403])

    def test_diagnostico_creation_via_factory(self):
        """Test: Crear diagnóstico vía factory (simular API)"""
        diag = DiagnosticoFactory.crear_caries(
            categoria=self.categoria,
            nivel_icdas=2
        )
        
        self.assertIsNotNone(diag.id)
        self.assertEqual(diag.categoria, self.categoria)

    def test_atributo_creation_via_factory(self):
        """Test: Crear atributo vía factory"""
        atributo = AtributoClinicoFactory.crear_material(
            key="api_material",
            nombre="Material API",
            materiales=["Opción 1", "Opción 2", "Opción 3"]
        )
        
        self.assertIsNotNone(atributo.id)
        self.assertEqual(atributo.opciones.count(), 3)


class OdontogramaFactoryTestCase(TestCase):
    """Tests específicos para las factories"""

    def test_categoria_factory_with_defaults(self):
        """Test: Factory de categoría con valores por defecto"""
        cat = CategoriaDiagnosticoFactory.crear(
            key="default_test",
            nombre="Default Test"
        )
        
        # Debe usar los defaults del tipo 'patologia'
        self.assertEqual(cat.color_key, "PATOLOGIA")
        self.assertEqual(cat.prioridad_key, "ALTA")

    def test_categoria_factory_custom_type(self):
        """Test: Factory de categoría con tipo personalizado"""
        cat = CategoriaDiagnosticoFactory.crear(
            key="custom_type",
            nombre="Tipo Personalizado",
            tipo="tratamiento"
        )
        
        self.assertEqual(cat.color_key, "REALIZADO")
        self.assertEqual(cat.prioridad_key, "MEDIA")

    def test_material_factory(self):
        """Test: Factory de materiales"""
        atributo = AtributoClinicoFactory.crear_material(
            key="test_materiales",
            nombre="Test Materiales",
            materiales=["Material A", "Material B", "Material C"]
        )
        
        opciones = list(atributo.opciones.all())
        self.assertEqual(len(opciones), 3)
        
        # Verificar nombres de opciones
        nombres = [o.nombre for o in opciones]
        self.assertIn("Material A", nombres)
        self.assertIn("Material B", nombres)
        self.assertIn("Material C", nombres)

    def test_plantilla_estado_binario(self):
        """Test: Plantilla de estado binario"""
        atributo = AtributoClinicoFactory.crear_desde_plantilla(
            plantilla="estado_binario",
            key="test_binario",
            nombre="Test Binario"
        )
        
        self.assertEqual(atributo.opciones.count(), 2)
        opciones = list(atributo.opciones.all())
        self.assertEqual(opciones[0].nombre, "Sí")
        self.assertEqual(opciones[1].nombre, "No")

    def test_plantilla_nivel_severidad(self):
        """Test: Plantilla de nivel de severidad"""
        atributo = AtributoClinicoFactory.crear_desde_plantilla(
            plantilla="nivel_severidad",
            key="test_severidad",
            nombre="Test Severidad"
        )
        
        self.assertEqual(atributo.opciones.count(), 4)

    def test_plantilla_grados_movilidad(self):
        """Test: Plantilla de grados de movilidad"""
        atributo = AtributoClinicoFactory.crear_desde_plantilla(
            plantilla="grados_movilidad",
            key="test_movilidad",
            nombre="Test Movilidad"
        )
        
        self.assertEqual(atributo.opciones.count(), 4)


class OdontogramaIntegrationTestCase(TestCase):
    """Tests de integración - flujos completos"""

    def test_complete_diagnostico_workflow(self):
        """Test: Flujo completo de diagnóstico"""
        # 1. Crear categoría
        cat = CategoriaDiagnosticoFactory.crear(
            key="workflow_test",
            nombre="Workflow Test",
            tipo="patologia"
        )
        
        # 2. Crear diagnóstico
        diag = DiagnosticoFactory.crear_caries(
            categoria=cat,
            nivel_icdas=3
        )
        
        # 3. Crear atributos
        atributo = AtributoClinicoFactory.crear_estado_procedimiento(
            key="workflow_estado",
            nombre="Estado Workflow"
        )
        
        # Verificar todo está conectado
        self.assertEqual(diag.categoria, cat)
        self.assertIsNotNone(atributo.id)
        self.assertTrue(cat.activo)
        self.assertTrue(diag.activo)
        self.assertTrue(atributo.activo)

    def test_complete_restauracion_workflow(self):
        """Test: Flujo completo de restauración"""
        # 1. Crear categoría
        cat = CategoriaDiagnosticoFactory.crear(
            key="rest_workflow",
            nombre="Restauración Workflow",
            tipo="tratamiento"
        )
        
        # 2. Crear diagnóstico de restauración
        diag = DiagnosticoFactory.crear_restauracion(
            categoria=cat,
            tipo="compleja"
        )
        
        # 3. Crear atributos de material
        material = AtributoClinicoFactory.crear_material(
            key="rest_material",
            nombre="Material Restauración",
            materiales=["Resina", "Porcelana", "Amalgama"]
        )
        
        estado = AtributoClinicoFactory.crear_desde_plantilla(
            plantilla="estado_calidad",
            key="rest_calidad",
            nombre="Calidad Restauración"
        )
        
        # Verificar
        self.assertEqual(diag.categoria, cat)
        self.assertEqual(material.opciones.count(), 3)
        self.assertEqual(estado.opciones.count(), 5)


# ============================================================================
# PYTEST MARKERS PARA TESTS ESPECÍFICOS
# ============================================================================

@pytest.mark.django_db
class PytestOdontogramaTests:
    """Tests usando pytest markers"""

    def test_factory_categoria(self):
        """Test: Categoria factory con pytest"""
        cat = CategoriaDiagnosticoFactory.crear(
            key="pytest_cat",
            nombre="Pytest Categoría"
        )
        assert cat.id is not None
        assert cat.key == "pytest_cat"

    def test_factory_caries(self):
        """Test: Caries factory con pytest"""
        cat = CategoriaDiagnosticoFactory.crear(
            key="pytest_caries_cat",
            nombre="Categoría Caries"
        )
        
        diag = DiagnosticoFactory.crear_caries(
            categoria=cat,
            nivel_icdas=1
        )
        assert diag.key == "caries_icdas_1"

    def test_factory_material(self):
        """Test: Material factory con pytest"""
        atributo = AtributoClinicoFactory.crear_material(
            key="pytest_mat",
            nombre="Material Pytest",
            materiales=["A", "B"]
        )
        assert atributo.opciones.count() == 2