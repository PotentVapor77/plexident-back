"""
Management command para cargar datos del odontograma desde archivos CSV
Uso: python manage.py cargar_odontograma_csv

Archivos CSV esperados en: api/odontogram/data/
"""
## api/odontogram/management/commands/cargar_odontograma_csv.py
import csv
import os
from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import transaction

from api.odontogram.models import (
    AreaAfectada,
    CategoriaDiagnostico,
    Diagnostico,
    TipoAtributoClinico,
    OpcionAtributoClinico,
    DiagnosticoAreaAfectada,
    DiagnosticoAtributoClinico,
)


class Command(BaseCommand):
    help = 'Carga datos del odontograma desde archivos CSV'

    def __init__(self):
        super().__init__()
        # Ruta a la carpeta de datos CSV
        self.data_dir = Path(__file__).resolve().parent.parent.parent / 'data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Limpia los datos existentes antes de cargar',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n🦷 Cargando datos del odontograma desde CSV...\n'))

        try:
            # Verificar que exista la carpeta de datos
            if not self.data_dir.exists():
                self.stdout.write(self.style.ERROR(f'❌ Carpeta {self.data_dir} no existe'))
                return

            # Limpiar datos si se solicita
            if options['clear']:
                self.stdout.write(self.style.WARNING('Limpiando datos existentes...'))
                self._clear_data()

            # Cargar datos en orden correcto
            with transaction.atomic():
                self._load_areas()
                self._load_tipos_atributos()
                self._load_opciones_atributos()
                self._load_categorias()
                self._load_diagnosticos()
                self._load_diagnostico_areas()
                self._load_diagnostico_atributos()

            self.stdout.write(self.style.SUCCESS('\n✅ Carga completada exitosamente\n'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Error: {str(e)}\n'))
            raise

    def _clear_data(self):
        """Limpia todos los datos del odontograma"""
        DiagnosticoAreaAfectada.objects.all().delete()
        DiagnosticoAtributoClinico.objects.all().delete()
        Diagnostico.objects.all().delete()
        CategoriaDiagnostico.objects.all().delete()
        OpcionAtributoClinico.objects.all().delete()
        TipoAtributoClinico.objects.all().delete()
        AreaAfectada.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('✓ Datos limpiados'))

    def _load_csv(self, filename):
        """Carga un archivo CSV y retorna una lista de diccionarios"""
        filepath = self.data_dir / filename

        if not filepath.exists():
            self.stdout.write(self.style.WARNING(f'⚠️  Archivo no encontrado: {filename}'))
            return []

        rows = []
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)

        return rows

    def _parse_bool(self, value):
        """Convierte cadena a booleano"""
        return str(value).lower() in ('true', '1', 'yes', 'on')

    def _parse_int(self, value):
        """Convierte cadena a entero, retorna None si está vacío"""
        if not value or value.strip() == '':
            return None
        return int(value)

    def _load_areas(self):
        """Carga áreas afectadas desde CSV"""
        rows = self._load_csv('areas_afectadas.csv')

        for row in rows:
            area, created = AreaAfectada.objects.get_or_create(
                key=row['key'],
                defaults={
                    'nombre': row['nombre'],
                    'activo': self._parse_bool(row.get('activo', True)),
                }
            )
            if created:
                self.stdout.write(f'  ✓ Área: {area.nombre}')

    def _load_tipos_atributos(self):
        """Carga tipos de atributos clínicos desde CSV"""
        rows = self._load_csv('tipos_atributos.csv')

        for row in rows:
            tipo, created = TipoAtributoClinico.objects.get_or_create(
                key=row['key'],
                defaults={
                    'nombre': row['nombre'],
                    'descripcion': row.get('descripcion', ''),
                    'activo': self._parse_bool(row.get('activo', True)),
                }
            )
            if created:
                self.stdout.write(f'  ✓ Tipo de atributo: {tipo.nombre}')

    def _load_opciones_atributos(self):
        """Carga opciones de atributos desde CSV"""
        rows = self._load_csv('opciones_atributos.csv')

        for row in rows:
            try:
                tipo = TipoAtributoClinico.objects.get(key=row['tipo_atributo_key'])

                opcion, created = OpcionAtributoClinico.objects.get_or_create(
                    tipo_atributo=tipo,
                    key=row['key'],
                    defaults={
                        'nombre': row['nombre'],
                        'prioridad': self._parse_int(row.get('prioridad')),
                        'orden': int(row.get('orden', 0)),
                        'activo': self._parse_bool(row.get('activo', True)),
                    }
                )
                if created:
                    self.stdout.write(f'    ✓ Opción: {opcion.nombre}')

            except TipoAtributoClinico.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f'⚠️  Tipo de atributo no encontrado: {row["tipo_atributo_key"]}'
                ))

    def _load_categorias(self):
        """Carga categorías de diagnóstico desde CSV"""
        rows = self._load_csv('categorias_diagnostico.csv')

        for row in rows:
            categoria, created = CategoriaDiagnostico.objects.get_or_create(
                key=row['key'],
                defaults={
                    'nombre': row['nombre'],
                    'color_key': row['color_key'],
                    'prioridad_key': row['prioridad_key'],
                    'activo': self._parse_bool(row.get('activo', True)),
                }
            )
            if created:
                self.stdout.write(f'✓ Categoría: {categoria.nombre}')

    def _load_diagnosticos(self):
        """Carga diagnósticos desde CSV"""
        rows = self._load_csv('diagnosticos.csv')

        for row in rows:
            try:
                categoria = CategoriaDiagnostico.objects.get(key=row['categoria_key'])

                diagnostico, created = Diagnostico.objects.get_or_create(
                    key=row['key'],
                    defaults={
                        'categoria': categoria,
                        'nombre': row['nombre'],
                        'siglas': row.get('siglas', ''),
                        'simbolo_color': row['simbolo_color'],
                        'prioridad': int(row['prioridad']),
                        'activo': self._parse_bool(row.get('activo', True)),
                    }
                )
                if created:
                    self.stdout.write(f'  ✓ Diagnóstico: {diagnostico.nombre}')

            except CategoriaDiagnostico.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f'⚠️  Categoría no encontrada: {row["categoria_key"]}'
                ))

    def _load_diagnostico_areas(self):
        """Carga relaciones diagnóstico-área desde CSV"""
        rows = self._load_csv('diagnostico_areas.csv')

        for row in rows:
            try:
                diagnostico = Diagnostico.objects.get(key=row['diagnostico_key'])
                area = AreaAfectada.objects.get(key=row['area_key'])

                DiagnosticoAreaAfectada.objects.get_or_create(
                    diagnostico=diagnostico,
                    area=area
                )

            except (Diagnostico.DoesNotExist, AreaAfectada.DoesNotExist) as e:
                self.stdout.write(self.style.WARNING(
                    f'⚠️  No se pudo crear relación: {row["diagnostico_key"]}'
                ))

    def _load_diagnostico_atributos(self):
        """Carga relaciones diagnóstico-atributo desde CSV"""
        rows = self._load_csv('diagnostico_atributos.csv')

        for row in rows:
            try:
                diagnostico = Diagnostico.objects.get(key=row['diagnostico_key'])
                tipo_atributo = TipoAtributoClinico.objects.get(
                    key=row['tipo_atributo_key']
                )

                DiagnosticoAtributoClinico.objects.get_or_create(
                    diagnostico=diagnostico,
                    tipo_atributo=tipo_atributo
                )

            except (Diagnostico.DoesNotExist, TipoAtributoClinico.DoesNotExist):
                self.stdout.write(self.style.WARNING(
                    f'⚠️  No se pudo crear relación: {row["diagnostico_key"]}'
                ))
