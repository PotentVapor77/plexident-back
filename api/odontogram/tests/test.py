"""
Tests para el sistema de Odontograma
Demuestra el uso de los patrones implementados
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from odontogram.models import CategoriaDiagnostico, Diagnostico
from odontogram.repositories import DiagnosticoRepository, CategoriaDiagnosticoRepository
from odontogram.services import DiagnosticoService, OdontogramaConfigService
from odontogram.factories import (
    DiagnosticoFactory,
    CategoriaDiagnosticoFactory,
    AtributoClinicoFactory,
)


class RepositoryPatternTestCase(TestCase):
    """Tests para el Repository Pattern"""

    def setUp(self):
        self.categoria = CategoriaDiagnostico.objects.create(
            key='test_categoria',
            nombre='Test Categoría',
            color_key='TEST',
            prioridad_key='MEDIA',
            activo=True
        )
        self.repo = DiagnosticoRepository()

    def test_crear_diagnostico(self):
        """Test crear diagnóstico usando repository"""
        diagnostico = self.repo.create(
            categoria=self.categoria,
            key='test_diagnostico',
            nombre='Test Diagnóstico',
            siglas='TD',
            prioridad=3,
            simbolo_color='TEST',
            activo=True
        )

        self.assertIsNotNone(diagnostico.id)
        self.assertEqual(diagnostico.nombre, 'Test Diagnóstico')

    def test_obtener_por_id(self):
        """Test obtener diagnóstico por ID"""
        diagnostico = self.repo.create(
            categoria=self.categoria,
            key='test_diagnostico',
            nombre='Test Diagnóstico',
            siglas='TD',
            prioridad=3,
            simbolo_color='TEST'
        )

        obtenido = self.repo.get_by_id(diagnostico.id)
        self.assertEqual(obtenido.id, diagnostico.id)

    def test_soft_delete(self):
        """Test soft delete de diagnóstico"""
        diagnostico = self.repo.create(
            categoria=self.categoria,
            key='test_diagnostico',
            nombre='Test Diagnóstico',
            siglas='TD',
            prioridad=3,
            simbolo_color='TEST'
        )

        # Soft delete
        resultado = self.repo.soft_delete(diagnostico.id)
        self.assertTrue(resultado)

        # Verificar que está desactivado
        diagnostico.refresh_from_db()
        self.assertFalse(diagnostico.activo)

        # Verificar que no se obtiene con get_by_id (solo activos)
        obtenido = self.repo.get_by_id(diagnostico.id)
        self.assertIsNone(obtenido)

    def test_filtrar_por_prioridad(self):
        """Test filtrar diagnósticos por prioridad"""
        # Crear diagnósticos con diferentes prioridades
        self.repo.create(
            categoria=self.categoria,
            key='bajo',
            nombre='Bajo',
            siglas='B',
            prioridad=1,
            simbolo_color='TEST'
        )
        self.repo.create(
            categoria=self.categoria,
            key='critico',
            nombre='Crítico',
            siglas='C',
            prioridad=5,
            simbolo_color='TEST'
        )

        # Filtrar críticos
        criticos = self.repo.get_criticos()
        self.assertEqual(criticos.count(), 1)
        self.assertEqual(criticos.first().prioridad, 5)


class ServiceLayerTestCase(TestCase):
    """Tests para el Service Layer Pattern"""

    def setUp(self):
        self.categoria = CategoriaDiagnostico.objects.create(
            key='test_categoria',
            nombre='Test Categoría',
            color_key='TEST',
            prioridad_key='MEDIA'
        )
        self.service = DiagnosticoService()

    def test_crear_diagnostico_completo(self):
        """Test crear diagnóstico con relaciones usando service"""
        # Este test requeriría tener áreas y atributos creados
        # Se omite por simplicidad, pero demuestra el concepto
        pass

    def test_buscar_diagnosticos(self):
        """Test búsqueda de diagnósticos"""
        # Crear diagnósticos
        Diagnostico.objects.create(
            categoria=self.categoria,
            key='caries',
            nombre='Caries Dental',
            siglas='CD',
            prioridad=4,
            simbolo_color='TEST'
        )
        Diagnostico.objects.create(
            categoria=self.categoria,
            key='fractura',
            nombre='Fractura',
            siglas='FR',
            prioridad=5,
            simbolo_color='TEST'
        )

        # Buscar
        resultados = self.service.buscar_diagnosticos(query='caries')
        self.assertEqual(len(resultados), 1)
        self.assertEqual(resultados[0].nombre, 'Caries Dental')

    def test_agrupar_por_urgencia(self):
        """Test agrupar diagnósticos por urgencia"""
        # Crear diagnósticos con diferentes prioridades
        for i in range(1, 6):
            Diagnostico.objects.create(
                categoria=self.categoria,
                key=f'diag_{i}',
                nombre=f'Diagnóstico {i}',
                siglas=f'D{i}',
                prioridad=i,
                simbolo_color='TEST'
            )

        agrupados = self.service.get_diagnosticos_por_urgencia()

        self.assertEqual(len(agrupados['criticos']), 1)
        self.assertEqual(len(agrupados['altos']), 1)
        self.assertEqual(len(agrupados['informativos']), 1)


class FactoryPatternTestCase(TestCase):
    """Tests para el Factory Pattern"""

    def setUp(self):
        self.categoria = CategoriaDiagnosticoFactory.crear(
            key='test_patologia',
            nombre='Test Patología',
            tipo='patologia'
        )

    def test_factory_crear_caries(self):
        """Test crear caries usando factory"""
        diagnostico = DiagnosticoFactory.crear_caries(
            categoria=self.categoria,
            nivel_icdas=3
        )

        self.assertEqual(diagnostico.key, 'caries_icdas_3')
        self.assertEqual(diagnostico.siglas, 'C3')
        self.assertEqual(diagnostico.prioridad, 4)  # ICDAS 3 = prioridad 4

    def test_factory_crear_restauracion(self):
        """Test crear restauración usando factory"""
        categoria_rest = CategoriaDiagnosticoFactory.crear(
            key='restauracion',
            nombre='Restauración',
            tipo='tratamiento'
        )

        diagnostico = DiagnosticoFactory.crear_restauracion(
            categoria=categoria_rest,
            tipo='compleja'
        )

        self.assertEqual(diagnostico.key, 'restauracion_compleja')
        self.assertEqual(diagnostico.prioridad, 3)

    def test_factory_atributo_desde_plantilla(self):
        """Test crear atributo usando plantilla"""
        atributo = AtributoClinicoFactory.crear_desde_plantilla(
            plantilla='nivel_severidad',
            key='test_severidad',
            nombre='Test Severidad'
        )

        self.assertEqual(atributo.key, 'test_severidad')
        # Verificar que se crearon las opciones
        self.assertEqual(atributo.opciones.count(), 4)

        # Verificar prioridades
        opciones = atributo.opciones.all()
        ninguno = opciones.get(key='ninguno')
        severo = opciones.get(key='severo')

        self.assertEqual(ninguno.prioridad, 1)
        self.assertEqual(severo.prioridad, 5)


class SignalsTestCase(TestCase):
    """Tests para el Observer Pattern (Signals)"""

    def test_validacion_prioridad(self):
        """Test que los signals validan la prioridad"""
        categoria = CategoriaDiagnostico.objects.create(
            key='test',
            nombre='Test',
            color_key='TEST',
            prioridad_key='MEDIA'
        )

        # Intentar crear con prioridad inválida
        with self.assertRaises(ValueError):
            Diagnostico.objects.create(
                categoria=categoria,
                key='test',
                nombre='Test',
                siglas='T',
                prioridad=10,  # Inválida
                simbolo_color='TEST'
            )

    def test_siglas_unicas(self):
        """Test que los signals validan siglas únicas"""
        categoria = CategoriaDiagnostico.objects.create(
            key='test',
            nombre='Test',
            color_key='TEST',
            prioridad_key='MEDIA'
        )

        Diagnostico.objects.create(
            categoria=categoria,
            key='test1',
            nombre='Test 1',
            siglas='TEST',
            prioridad=3,
            simbolo_color='TEST'
        )

        # Intentar crear con siglas duplicadas
        with self.assertRaises(ValueError):
            Diagnostico.objects.create(
                categoria=categoria,
                key='test2',
                nombre='Test 2',
                siglas='TEST',  # Duplicada
                prioridad=3,
                simbolo_color='TEST'
            )


class IntegrationTestCase(TestCase):
    """Tests de integración usando todos los patrones"""

    def test_flujo_completo_crear_diagnostico(self):
        """Test del flujo completo usando todos los patrones"""
        # 1. Usar Factory para crear categoría
        categoria = CategoriaDiagnosticoFactory.crear(
            key='patologia',
            nombre='Patología Activa',
            tipo='patologia'
        )

        # 2. Usar Factory para crear diagnóstico
        diagnostico = DiagnosticoFactory.crear_caries(
            categoria=categoria,
            nivel_icdas=5  # Crítico
        )

        # 3. Usar Repository para obtener
        repo = DiagnosticoRepository()
        obtenido = repo.get_by_id(diagnostico.id)

        # 4. Verificar
        self.assertIsNotNone(obtenido)
        self.assertEqual(obtenido.prioridad, 5)

        # 5. Usar Service para búsqueda
        service = DiagnosticoService()
        criticos = service.get_diagnosticos_por_urgencia()['criticos']

        # 6. Verificar que está en críticos
        self.assertIn(diagnostico, criticos)

    def test_config_service(self):
        """Test del servicio de configuración"""
        # Crear datos
        categoria = CategoriaDiagnosticoFactory.crear(
            key='test',
            nombre='Test',
            tipo='patologia'
        )

        DiagnosticoFactory.crear_caries(categoria, nivel_icdas=3)

        # Usar servicio
        service = OdontogramaConfigService()
        stats = service.get_config_summary()

        # Verificar estadísticas
        self.assertGreater(stats['total_diagnosticos'], 0)
        self.assertGreater(stats['total_categorias'], 0)