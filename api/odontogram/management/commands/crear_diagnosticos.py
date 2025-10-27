"""
Management command para crear diagnósticos usando el Factory Pattern
python manage.py crear_diagnosticos
"""

from django.core.management.base import BaseCommand
from api.odontogram.factories import (
    DiagnosticoFactory,
    AtributoClinicoFactory,
    CategoriaDiagnosticoFactory,
    ConfiguracionInicialFactory,
)
from odontogram.models import CategoriaDiagnostico


class Command(BaseCommand):
    help = 'Crea diagnósticos y configuración usando Factory Pattern'

    def add_arguments(self, parser):
        parser.add_argument(
            '--tipo',
            type=str,
            default='basico',
            choices=['basico', 'completo', 'caries', 'restauraciones'],
            help='Tipo de configuración a crear'
        )

    def handle(self, *args, **options):
        tipo = options['tipo']

        if tipo == 'basico':
            self.crear_configuracion_basica()
        elif tipo == 'completo':
            self.crear_configuracion_completa()
        elif tipo == 'caries':
            self.crear_caries()
        elif tipo == 'restauraciones':
            self.crear_restauraciones()

        self.stdout.write(self.style.SUCCESS('Configuración creada exitosamente'))

    def crear_configuracion_basica(self):
        """Crea configuración básica usando el factory"""
        self.stdout.write('Creando configuración básica...')
        resultado = ConfiguracionInicialFactory.crear_configuracion_basica()
        self.stdout.write(self.style.SUCCESS(f'✓ {resultado}'))

    def crear_configuracion_completa(self):
        """Crea configuración completa"""
        self.stdout.write('Creando configuración completa...')

        # Crear categorías
        categorias = {
            'patologia': CategoriaDiagnosticoFactory.crear(
                key='patologia_activa',
                nombre='Patología Activa',
                tipo='patologia'
            ),
            'restauracion': CategoriaDiagnosticoFactory.crear(
                key='restauracion',
                nombre='Restauración',
                tipo='tratamiento'
            ),
            'endodoncia': CategoriaDiagnosticoFactory.crear(
                key='endodoncia',
                nombre='Endodoncia',
                tipo='endodoncia'
            ),
            'ausencia': CategoriaDiagnosticoFactory.crear(
                key='ausencia',
                nombre='Ausencia',
                tipo='ausencia'
            ),
        }

        self.stdout.write(f'✓ {len(categorias)} categorías creadas')

        # Crear diagnósticos de caries (ICDAS 1-6)
        for nivel in range(1, 7):
            DiagnosticoFactory.crear_caries(
                categoria=categorias['patologia'],
                nivel_icdas=nivel
            )
        self.stdout.write('✓ 6 diagnósticos de caries creados')

        # Crear restauraciones
        tipos_rest = ['simple', 'compleja', 'provisional', 'definitiva']
        for tipo in tipos_rest:
            DiagnosticoFactory.crear_restauracion(
                categoria=categorias['restauracion'],
                tipo=tipo
            )
        self.stdout.write(f'✓ {len(tipos_rest)} tipos de restauración creados')

        # Crear atributos
        AtributoClinicoFactory.crear_material(
            key='material_restauracion',
            nombre='Material de Restauración',
            materiales=['Amalgama', 'Resina', 'Porcelana', 'Oro', 'Ionómero', 'Composite']
        )

        AtributoClinicoFactory.crear_desde_plantilla(
            plantilla='estado_calidad',
            key='estado_restauracion',
            nombre='Estado de Restauración'
        )

        AtributoClinicoFactory.crear_estado_procedimiento(
            key='estado_procedimiento',
            nombre='Estado del Procedimiento'
        )

        AtributoClinicoFactory.crear_desde_plantilla(
            plantilla='nivel_severidad',
            key='dolor',
            nombre='Nivel de Dolor'
        )

        AtributoClinicoFactory.crear_desde_plantilla(
            plantilla='grados_movilidad',
            key='movilidad',
            nombre='Grado de Movilidad'
        )

        self.stdout.write('✓ 5 tipos de atributos clínicos creados')

    def crear_caries(self):
        """Crea solo diagnósticos de caries"""
        self.stdout.write('Creando diagnósticos de caries...')

        try:
            categoria = CategoriaDiagnostico.objects.get(key='patologia_activa')
        except CategoriaDiagnostico.DoesNotExist:
            categoria = CategoriaDiagnosticoFactory.crear(
                key='patologia_activa',
                nombre='Patología Activa',
                tipo='patologia'
            )

        for nivel in range(1, 7):
            diagnostico = DiagnosticoFactory.crear_caries(
                categoria=categoria,
                nivel_icdas=nivel
            )
            self.stdout.write(f'✓ Creado: {diagnostico.nombre}')

    def crear_restauraciones(self):
        """Crea solo diagnósticos de restauración"""
        self.stdout.write('Creando diagnósticos de restauración...')

        try:
            categoria = CategoriaDiagnostico.objects.get(key='restauracion')
        except CategoriaDiagnostico.DoesNotExist:
            categoria = CategoriaDiagnosticoFactory.crear(
                key='restauracion',
                nombre='Restauración',
                tipo='tratamiento'
            )

        tipos = ['simple', 'compleja', 'provisional', 'definitiva']
        for tipo in tipos:
            diagnostico = DiagnosticoFactory.crear_restauracion(
                categoria=categoria,
                tipo=tipo
            )
            self.stdout.write(f'✓ Creado: {diagnostico.nombre}')